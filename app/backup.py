"""
SafingData — Motor de backup/restore SSH via SFTP (paramiko).
Autenticación: contraseña, clave SSH, o agente SSH (Tailscale SSH).
Jump Host: soporta conexión a servidores en redes Tailscale sin tener el cliente
           instalado, usando un bastión intermedio via SSH ProxyCommand.
Backup: completo (sin incremental).
"""

import os
import shlex
import stat
import threading
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, List, Optional


class SSHBackupClient:
    """Cliente SSH/SFTP para operaciones de backup y restore."""

    def __init__(self) -> None:
        self._client = None
        self._sftp = None
        self.connected: bool = False
        self._cancel_flag: threading.Event = threading.Event()

    # ──────────────────────────────────────────
    # Conexión
    # ──────────────────────────────────────────

    def connect(
        self,
        host: str,
        port: int,
        user: str,
        password: Optional[str] = None,
        jump_host: Optional[str] = None,
        jump_user: Optional[str] = None,
    ) -> None:
        """
        Establece la conexión SSH, con soporte opcional de Jump Host.

        Si ``jump_host`` está definido, la conexión se realiza en dos saltos:
          1. Se abre un túnel SSH hasta el bastión (``jump_host``).
          2. A través de ese túnel, se conecta al servidor destino (``host``).
        Esto permite llegar a nodos de una red Tailscale sin tener el cliente
        de Tailscale instalado en la máquina local.

        Si ``password`` es None o cadena vacía, se intenta autenticación
        mediante agente SSH del sistema (Tailscale SSH) o claves privadas
        del usuario (~/.ssh). Útil para redes Tailscale donde no se
        requiere contraseña explícita.
        """
        import paramiko

        use_password = bool(password)

        # ── Jump Host (ProxyCommand) ──────────────────────────────
        # Si se configura un bastión, construimos un socket de transporte
        # que "pasa" a través de él usando paramiko.ProxyCommand con el
        # comando nativo `ssh -W` (open_channel directo TCP al host destino).
        sock = None
        if jump_host:
            _jump_user = jump_user or user
            # El comando que el bastión ejecuta para establecer el canal TCP:
            # ssh -W <host>:<port> abre un canal raw hacia el destino final.
            proxy_cmd = (
                f"ssh -o StrictHostKeyChecking=no "
                f"-o UserKnownHostsFile=/dev/null "
                f"-W {host}:{port} "
                f"{_jump_user}@{jump_host}"
            )
            sock = paramiko.ProxyCommand(proxy_cmd)

        self._client = paramiko.SSHClient()
        # SEGURIDAD: WarningPolicy registra un aviso si la clave del host no está
        # en el known_hosts local, pero no bloquea la conexión. Es más seguro que
        # AutoAddPolicy (que acepta cualquier clave sin advertencia alguna).
        # Para máxima seguridad en entornos de producción, usa RejectPolicy y
        # carga las claves del servidor con load_host_keys() antes de conectar.
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(paramiko.WarningPolicy())
        self._client.connect(
            host,
            port=port,
            username=user,
            password=password if use_password else None,
            # Si no hay contraseña, intentar agente SSH y claves locales
            allow_agent=not use_password,
            look_for_keys=not use_password,
            timeout=30,
            banner_timeout=30,
            # sock=None → conexión directa; sock=ProxyCommand → via bastión
            sock=sock,
        )

        # Mantener la conexión viva para sesiones largas (p.ej. via Tailscale)
        transport = self._client.get_transport()
        if transport:
            transport.set_keepalive(15)

        self._sftp = self._client.open_sftp()
        self.connected = True
        self._cancel_flag.clear()

    def disconnect(self) -> None:
        """Cierra la conexión SSH/SFTP de forma limpia."""
        try:
            if self._sftp:
                self._sftp.close()
            if self._client:
                self._client.close()
        except Exception:
            pass
        finally:
            self._sftp = None
            self._client = None
            self.connected = False

    def cancel(self) -> None:
        """Señala al cliente que cancele la operación en curso."""
        self._cancel_flag.set()

    # ──────────────────────────────────────────
    # Información del servidor
    # ──────────────────────────────────────────

    def get_disk_info(self) -> Dict[str, int]:
        """
        Obtiene información de disco del servidor.
        Retorna: {'total': bytes, 'used': bytes, 'free': bytes}

        Usa ``df -P -k`` (formato POSIX, unidades en KB) para mayor
        compatibilidad con BusyBox, macOS y distros Linux poco comunes.
        """
        _, stdout, _ = self._client.exec_command(
            "df -P -k . 2>/dev/null | awk 'NR==2{print $2,$3,$4}'"
        )
        output = stdout.read().decode().strip()
        if not output:
            return {"total": 0, "used": 0, "free": 0}
        parts = output.split()
        if len(parts) < 3:
            return {"total": 0, "used": 0, "free": 0}
        try:
            # df -k devuelve KB → convertir a bytes multiplicando por 1024
            return {
                "total": int(parts[0]) * 1024,
                "used":  int(parts[1]) * 1024,
                "free":  int(parts[2]) * 1024,
            }
        except ValueError:
            return {"total": 0, "used": 0, "free": 0}

    def get_remote_home(self) -> str:
        """
        Obtiene el directorio home real del usuario en el servidor.

        Usa ``sftp.normalize('.')`` (protocolo SFTP nativo) en lugar de
        ``echo $HOME`` para evitar fallos con shells restrictivas o
        servidores que no exporten la variable de entorno.
        """
        try:
            return self._sftp.normalize(".")
        except Exception:
            # Fallback: intentar con el comando shell
            _, stdout, _ = self._client.exec_command("echo $HOME")
            result = stdout.read().decode().strip()
            return result or "/"

    def resolve_remote_base(self, remote_base: str) -> str:
        """Convierte remote_base relativo al home en path absoluto."""
        home = self.get_remote_home()
        return str(PurePosixPath(home) / remote_base)

    def list_backups(self, remote_base_abs: str) -> List[str]:
        """Lista las sesiones de backup en el servidor."""
        try:
            entries = self._sftp.listdir_attr(remote_base_abs)
            dirs = [
                e.filename
                for e in entries
                if stat.S_ISDIR(e.st_mode)
            ]
            dirs.sort(reverse=True)
            return dirs
        except FileNotFoundError:
            return []
        except Exception:
            return []

    # ──────────────────────────────────────────
    # Helpers de directorio remoto
    # ──────────────────────────────────────────

    def _ensure_dir(self, remote_path: str) -> None:
        """Crea directorios remotos recursivamente (equivalente a mkdir -p)."""
        # SEGURIDAD: shlex.quote escapa la ruta para prevenir inyección de comandos
        # si el path contiene caracteres especiales como comillas simples, punto y
        # coma, o backticks que podrían ejecutar comandos arbitrarios en el servidor.
        self._client.exec_command(f"mkdir -p {shlex.quote(remote_path)}")
        # Esperamos que se complete
        import time
        time.sleep(0.05)

    # ──────────────────────────────────────────
    # Upload
    # ──────────────────────────────────────────

    def upload_path(
        self,
        local_path: str,
        remote_base: str,
        progress_cb: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        """
        Sube un archivo o carpeta completa al servidor.

        progress_cb(filename, bytes_transferred, bytes_total)
        """
        local = Path(local_path)
        if not local.exists():
            raise FileNotFoundError(f"No existe: {local_path}")

        self._ensure_dir(remote_base)

        if local.is_file():
            self._upload_file(local, remote_base, progress_cb)
        elif local.is_dir():
            self._upload_dir(local, remote_base, progress_cb)

    def _upload_file(
        self,
        local_file: Path,
        remote_dir: str,
        progress_cb: Optional[Callable],
    ) -> None:
        if self._cancel_flag.is_set():
            raise InterruptedError("Backup cancelado por el usuario.")

        remote_path = str(PurePosixPath(remote_dir) / local_file.name)
        size = local_file.stat().st_size

        def _cb(transferred: int, total: int) -> None:
            if self._cancel_flag.is_set():
                raise InterruptedError("Backup cancelado por el usuario.")
            if progress_cb:
                progress_cb(local_file.name, transferred, total)

        self._sftp.put(str(local_file), remote_path, callback=_cb)

    def _upload_dir(
        self,
        local_dir: Path,
        remote_base: str,
        progress_cb: Optional[Callable],
    ) -> None:
        remote_dir = str(PurePosixPath(remote_base) / local_dir.name)
        self._ensure_dir(remote_dir)

        for item in sorted(local_dir.iterdir()):
            if self._cancel_flag.is_set():
                raise InterruptedError("Backup cancelado por el usuario.")
            if item.is_file():
                self._upload_file(item, remote_dir, progress_cb)
            elif item.is_dir():
                self._upload_dir(item, remote_dir, progress_cb)

    # ──────────────────────────────────────────
    # Download
    # ──────────────────────────────────────────

    def download_path(
        self,
        remote_path: str,
        local_base: str,
        progress_cb: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        """
        Descarga un archivo o carpeta remota al directorio local_base.
        """
        local_base_path = Path(local_base)
        local_base_path.mkdir(parents=True, exist_ok=True)

        try:
            attrs = self._sftp.lstat(remote_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"No existe en el servidor: {remote_path}")

        if stat.S_ISDIR(attrs.st_mode):
            folder_name = PurePosixPath(remote_path).name
            self._download_dir(remote_path, local_base_path / folder_name, progress_cb)
        else:
            fname = PurePosixPath(remote_path).name
            local_file = local_base_path / fname
            self._sftp.get(remote_path, str(local_file), callback=progress_cb)

    def _download_dir(
        self,
        remote_dir: str,
        local_dir: Path,
        progress_cb: Optional[Callable],
    ) -> None:
        local_dir.mkdir(parents=True, exist_ok=True)
        try:
            entries = self._sftp.listdir_attr(remote_dir)
        except Exception:
            return

        for entry in entries:
            if self._cancel_flag.is_set():
                raise InterruptedError("Descarga cancelada por el usuario.")

            # SEGURIDAD: Path(entry.filename).name extrae solo el componente final
            # del nombre. Esto previene ataques de Path Traversal donde un servidor
            # SFTP malicioso devuelve nombres como "../../../etc/passwd" para
            # sobrescribir archivos fuera del directorio de destino.
            safe_name = Path(entry.filename).name
            if not safe_name or safe_name in (".", ".."):
                continue

            remote_item = str(PurePosixPath(remote_dir) / entry.filename)
            local_item = local_dir / safe_name

            if stat.S_ISDIR(entry.st_mode):
                self._download_dir(remote_item, local_item, progress_cb)
            else:
                def _cb(transferred: int, total: int, fn: str = safe_name) -> None:
                    if self._cancel_flag.is_set():
                        raise InterruptedError("Descarga cancelada.")
                    if progress_cb:
                        progress_cb(fn, transferred, total)

                self._sftp.get(remote_item, str(local_item), callback=_cb)

    # ──────────────────────────────────────────
    # Eliminación
    # ──────────────────────────────────────────

    def delete_remote_path(self, remote_path: str) -> None:
        """Elimina recursivamente un path en el servidor."""
        try:
            attrs = self._sftp.lstat(remote_path)
        except FileNotFoundError:
            return

        if stat.S_ISDIR(attrs.st_mode):
            self._rmdir_recursive(remote_path)
        else:
            self._sftp.remove(remote_path)

    def _rmdir_recursive(self, remote_path: str) -> None:
        try:
            entries = self._sftp.listdir_attr(remote_path)
        except Exception:
            return

        for entry in entries:
            item_path = str(PurePosixPath(remote_path) / entry.filename)
            if stat.S_ISDIR(entry.st_mode):
                self._rmdir_recursive(item_path)
            else:
                self._sftp.remove(item_path)

        self._sftp.rmdir(remote_path)

    def exec(self, cmd: str) -> str:
        """Ejecuta un comando shell en el servidor y retorna su salida."""
        _, stdout, stderr = self._client.exec_command(cmd)
        return stdout.read().decode()
