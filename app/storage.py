"""
SafingData — Gestión de espacio y cuotas.
Calcula tamaño local y verifica disponibilidad en el servidor remoto.
"""

import os
from pathlib import Path
from typing import List, Tuple

SYSTEM_RESERVE_GB = 20
BYTES_PER_GB = 1024 ** 3


def get_local_size(paths: List[str]) -> int:
    """Calcula el tamaño total en bytes de todos los paths locales seleccionados."""
    total = 0
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                pass
        elif path.is_dir():
            for f in path.rglob("*"):
                if f.is_file():
                    try:
                        total += f.stat().st_size
                    except OSError:
                        pass
    return total


def count_local_files(paths: List[str]) -> int:
    """Cuenta el número total de archivos en los paths seleccionados."""
    count = 0
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        if path.is_file():
            count += 1
        elif path.is_dir():
            count += sum(1 for f in path.rglob("*") if f.is_file())
    return count


def check_quota(
    remote_total_bytes: int,
    remote_used_bytes: int,
    upload_size_bytes: int,
) -> Tuple[bool, int, str]:
    """
    Verifica si hay espacio suficiente en el servidor.

    Regla: disponible = total - 20 GB (reserva sistema) - usado
    Retorna: (ok, available_bytes, message)
    """
    reserve = SYSTEM_RESERVE_GB * BYTES_PER_GB
    available = remote_total_bytes - reserve - remote_used_bytes

    if available <= 0:
        return (
            False,
            0,
            f"Sin espacio disponible. Reserva del sistema: {SYSTEM_RESERVE_GB} GB aplicada.",
        )

    if upload_size_bytes > available:
        return (
            False,
            available,
            (
                f"Archivos seleccionados ({format_size(upload_size_bytes)}) superan "
                f"el espacio disponible ({format_size(available)})."
            ),
        )

    return True, available, f"Espacio disponible: {format_size(available)}"


def format_size(bytes_size: int) -> str:
    """Formatea bytes a una cadena legible."""
    if bytes_size < 0:
        return "0 B"
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 ** 2:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 ** 3:
        return f"{bytes_size / 1024 ** 2:.1f} MB"
    else:
        return f"{bytes_size / 1024 ** 3:.2f} GB"


def storage_bar_percent(
    remote_total_bytes: int,
    remote_used_bytes: int,
) -> Tuple[float, float]:
    """
    Retorna (used_pct, reserve_pct) como porcentajes del total.
    used_pct: porcentaje del espacio ya utilizado (sin reserva)
    reserve_pct: porcentaje que ocupa la reserva de 20 GB
    """
    if remote_total_bytes <= 0:
        return 0.0, 0.0
    used_pct = min(100.0, remote_used_bytes / remote_total_bytes * 100)
    reserve_pct = min(100.0, (SYSTEM_RESERVE_GB * BYTES_PER_GB) / remote_total_bytes * 100)
    return used_pct, reserve_pct
