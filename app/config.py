"""
SafingData — Gestión de configuración persistente.
Guarda y carga config.json desde la carpeta data/ del pendrive.
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

DEFAULT_CONFIG: dict = {
    "host": "190.220.229.45",
    "port": 3025,
    "user": "gabodev24",
    "remote_base": "safingdata_backups",   # relativo al home del servidor
    "selected_paths": [],
    "first_run": True,
}


def load_config() -> dict:
    """Carga la configuración desde config.json. Si no existe devuelve defaults."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
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
