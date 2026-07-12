"""
SafingData — Gestor de sesiones.
Registra cada backup.
"""

import json
from datetime import datetime, timedelta
import sys
from pathlib import Path
from typing import Dict, List

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent
SESSION_FILE = BASE_DIR / "data" / "session.json"

# ────────────────────────────────────────────────────────────
# Persistencia
# ────────────────────────────────────────────────────────────

def _load() -> Dict:
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save(data: Dict) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ────────────────────────────────────────────────────────────
# API pública
# ────────────────────────────────────────────────────────────

def record_backup(backup_id: str, paths: List[str], size_bytes: int) -> None:
    """Registra un nuevo backup completado."""
    session = _load()
    now = datetime.now()
    session[backup_id] = {
        "created_at": now.isoformat(),
        "paths": paths,
        "size_bytes": size_bytes,
        "deleted": False,
    }
    _save(session)


def get_all_backups() -> List[Dict]:
    """Devuelve todos los backups con información de estado."""
    session = _load()
    result = []
    for bid, info in session.items():
        try:
            created = datetime.fromisoformat(info["created_at"])
        except (KeyError, ValueError):
            continue
        result.append({
            "id": bid,
            "created_at": created,
            "size_bytes": info.get("size_bytes", 0),
            "paths": info.get("paths", []),
            "deleted": info.get("deleted", False),
        })
    # Más reciente primero
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result


def mark_deleted(backup_id: str) -> None:
    """Marca un backup como eliminado en la sesión local."""
    session = _load()
    if backup_id in session:
        session[backup_id]["deleted"] = True
    _save(session)


def delete_backup_record(backup_id: str) -> None:
    """Elimina completamente el registro de un backup."""
    session = _load()
    session.pop(backup_id, None)
    _save(session)


def has_active_backups() -> bool:
    """Devuelve True si hay al menos un backup activo (no eliminado)."""
    return any(
        not b["deleted"]
        for b in get_all_backups()
    )
