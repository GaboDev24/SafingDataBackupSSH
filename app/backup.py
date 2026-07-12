"""
SafingData — Motor de backup/restore SSH via SFTP (paramiko).
Autenticación: contraseña únicamente.
Backup: completo (sin incremental).
"""

import os
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

    def connect(self, host: str, port: int, user: str, password: str) -> None:
        """Establece la conexión SSH con contraseña."""
        import paramiko

        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            host,
            port=port,
            username=user,
            password=password,
            timeout=30,
            banner_timeout=30,
        )
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
        """
        # Usamos df sobre el home del usuario para obtener info real
        _, stdout, _ = self._client.exec_command(
            "df -B1 ~ 2>/dev/null | awk 'NR==2{print $2,$3,$4}'"
        )
        output = stdout.read().decode().strip()
        if not output:
            return {"total": 0, "used": 0, "free": 0}
        parts = output.split()
        if len(parts) < 3:
            return {"total": 0, "used": 0, "free": 0}
        try:
            return {
                "total": int(parts[0]),
                "used": int(parts[1]),
                "free": int(parts[2]),
            }
        except ValueError:
            return {"total": 0, "used": 0, "free": 0}

    def get_remote_home(self) -> str:
        """Obtiene el directorio home real del usuario en el servidor."""
        _, stdout, _ = self._client.exec_command("echo $HOME")
        return stdout.read().decode().strip()

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
        self._client.exec_command(f"mkdir -p '{remote_path}'")
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
            remote_item = str(PurePosixPath(remote_dir) / entry.filename)
            local_item = local_dir / entry.filename

            if stat.S_ISDIR(entry.st_mode):
                self._download_dir(remote_item, local_item, progress_cb)
            else:
                size = entry.st_size

                def _cb(transferred: int, total: int, fn: str = entry.filename) -> None:
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
