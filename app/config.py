"""
SafingData — Gestión de configuración persistente.
Guarda y carga config.json desde la carpeta data/ del pendrive.
Soporta múltiples máquinas SSH, cada una con un nombre clave único.
"""

import json
import sys
from pathlib import Path

# Directorio raíz del proyecto (el pendrive o ejecutable)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"

_DEFAULT_MACHINE: dict = {
    "name": "Servidor Principal",
    "host": "your.ssh.server.com",
    "port": 22,
    "user": "your_username",
    "remote_base": "safingdata_backups",
    # Campos opcionales para Jump Host (conexión a Tailscale sin cliente instalado).
    # Si jump_host está vacío, se conecta directamente al servidor.
    # Si está definido, la conexión pasa por el bastión: cliente → jump_host → host.
    "jump_host": "",
    "jump_user": "",
}

DEFAULT_CONFIG: dict = {
    "machines": [dict(_DEFAULT_MACHINE)],
    "active_machine": "Servidor Principal",
    "selected_paths": [],
    "first_run": True,
}


# ── Migración ────────────────────────────────────────────────

def _migrate_old_format(data: dict) -> dict:
    """Convierte config vieja (host/port/user sueltos) al nuevo formato con 'machines'."""
    if "machines" not in data:
        machine = {
            "name": "Servidor Principal",
            "host": data.pop("host", _DEFAULT_MACHINE["host"]),
            "port": data.pop("port", _DEFAULT_MACHINE["port"]),
            "user": data.pop("user", _DEFAULT_MACHINE["user"]),
            "remote_base": data.pop("remote_base", _DEFAULT_MACHINE["remote_base"]),
            "jump_host": "",
            "jump_user": "",
        }
        data["machines"] = [machine]
        data.setdefault("active_machine", machine["name"])
    else:
        # Migración hacia adelante: asegurar que máquinas existentes tengan los campos nuevos
        for m in data["machines"]:
            m.setdefault("jump_host", "")
            m.setdefault("jump_user", "")
    return data


# ── Carga / guardado ─────────────────────────────────────────

def load_config() -> dict:
    """Carga la configuración desde config.json. Si no existe devuelve defaults."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data = _migrate_old_format(data)
            # Merge: añadir claves nuevas que no existan aún
            for key, val in DEFAULT_CONFIG.items():
                data.setdefault(key, val)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    """Persiste la configuración en config.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False, default=str)


# ── Helpers de máquinas ──────────────────────────────────────

def get_active_machine(cfg: dict) -> dict:
    """Retorna el dict de la máquina activa, o la primera disponible."""
    machines = cfg.get("machines", [])
    active_name = cfg.get("active_machine", "")
    for m in machines:
        if m.get("name") == active_name:
            return m
    return machines[0] if machines else dict(_DEFAULT_MACHINE)


def get_machine_names(cfg: dict) -> list:
    """Retorna la lista de nombres/alias de las máquinas configuradas."""
    return [m.get("name", "Sin nombre") for m in cfg.get("machines", [])]


def set_active_machine(cfg: dict, name: str) -> None:
    """Establece la máquina activa por nombre."""
    cfg["active_machine"] = name


def upsert_machine(cfg: dict, machine: dict) -> None:
    """Inserta o actualiza una máquina por su nombre clave."""
    machines = cfg.setdefault("machines", [])
    for i, m in enumerate(machines):
        if m.get("name") == machine["name"]:
            machines[i] = machine
            return
    machines.append(machine)


def delete_machine(cfg: dict, name: str) -> bool:
    """Elimina una máquina por nombre. Retorna True si se eliminó."""
    machines = cfg.get("machines", [])
    new_list = [m for m in machines if m.get("name") != name]
    if len(new_list) == len(machines):
        return False
    cfg["machines"] = new_list
    # Si era la activa, elegir la primera disponible
    if cfg.get("active_machine") == name:
        cfg["active_machine"] = new_list[0]["name"] if new_list else ""
    return True
