"""
SafingData — Gestor de sesiones.
Registra cada backup y permite la sincronizacion con el servidor.
"""

import json
from datetime import datetime
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
# API publica
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
        "imported": False,
    }
    _save(session)


def get_all_backups() -> List[Dict]:
    """Devuelve todos los backups con informacion de estado."""
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
            "imported": info.get("imported", False),
        })
    # Mas reciente primero
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result


def mark_deleted(backup_id: str) -> None:
    """Marca un backup como eliminado en la sesion local."""
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


def sync_from_server(server_backup_ids: List[str]) -> int:
    """
    Fusiona la lista de IDs remotos con el registro local (session.json).

    Comportamiento:
    - Los IDs presentes en el servidor pero ausentes en el registro local
      se importan como nuevas entradas. La fecha se infiere del nombre cuando
      sigue el patron backup_YYYYMMDD_HHMMSS; de lo contrario se usa la
      fecha y hora actuales como valor de referencia.
    - Los registros locales cuyo ID ya no exista en el servidor se marcan
      como deleted=True, salvo que ya hubieran sido eliminados explicitamente.
    - El campo size_bytes de los backups importados se inicializa en 0 ya
      que determinar el tamano exacto requeriria explorar el servidor de
      forma recursiva.
    - El campo imported=True distingue estas entradas de los backups
      realizados originalmente desde esta maquina.

    Retorna el numero de entradas nuevas importadas.
    """
    session = _load()
    server_set = set(server_backup_ids)
    local_set = set(session.keys())

    imported_count = 0

    # Importar backups presentes en el servidor pero ausentes en el registro local
    for bid in server_backup_ids:
        if bid not in local_set:
            created_at = _infer_date(bid)
            session[bid] = {
                "created_at": created_at.isoformat(),
                "paths": [],
                "size_bytes": 0,
                "deleted": False,
                "imported": True,
            }
            imported_count += 1

    # Marcar como eliminados los registros locales que ya no existen en el servidor
    for bid in local_set:
        if bid not in server_set and not session[bid].get("deleted", False):
            session[bid]["deleted"] = True

    _save(session)
    return imported_count


def _infer_date(backup_id: str) -> datetime:
    """
    Intenta extraer la fecha y hora del nombre del backup.

    El formato esperado es backup_YYYYMMDD_HHMMSS. Si el nombre no sigue
    ese patron, retorna la fecha y hora actuales como valor de fallback.
    """
    try:
        return datetime.strptime(backup_id, "backup_%Y%m%d_%H%M%S")
    except ValueError:
        return datetime.now()
