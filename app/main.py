"""
SafingData — Punto de entrada principal.
Configura el sys.path para cargar libs/ del pendrive y lanza la GUI.
"""

import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    pass

# ────────────────────────────────────────────────────────────
# Configurar paths
# ────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
else:
    BASE_DIR = Path(__file__).parent.parent
LIBS_DIR = BASE_DIR / "libs"

# Insertar libs/ al frente del path para que paramiko y deps
# del pendrive tengan prioridad sobre el sistema
if LIBS_DIR.exists():
    sys.path.insert(0, str(LIBS_DIR))

# Añadir el directorio raíz del proyecto
sys.path.insert(0, str(BASE_DIR))


# ────────────────────────────────────────────────────────────
# Verificar dependencias críticas
# ────────────────────────────────────────────────────────────
def _check_deps() -> bool:
    try:
        import paramiko  # noqa: F401
        return True
    except ImportError:
        return False


def _show_dep_error() -> None:
    """Muestra un mensaje de error si faltan dependencias."""
    msg = (
        "SafingData requiere la librería 'paramiko' para funcionar.\n\n"
        "Para instalar las dependencias, ejecuta:\n\n"
        "  Windows:  setup_libs.bat\n"
        "  Linux:    ./setup_libs.sh\n\n"
        "O manualmente:\n"
        "  python setup_libs.py\n\n"
        "Asegúrate de tener conexión a internet para la instalación."
    )
    # Intentar mostrar con Tkinter
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Dependencias faltantes", msg)
        root.destroy()
    except Exception:
        print("\n" + "=" * 60)
        print("ERROR: Dependencias faltantes")
        print("=" * 60)
        print(msg)
        print("=" * 60)
        input("\nPresiona Enter para cerrar...")


# ────────────────────────────────────────────────────────────
# Verificar versión de Python
# ────────────────────────────────────────────────────────────
def _check_python() -> bool:
    return sys.version_info >= (3, 8)


def _show_python_error() -> None:
    print(f"ERROR: SafingData requiere Python 3.8 o superior.")
    print(f"  Versión actual: {sys.version}")
    input("\nPresiona Enter para cerrar...")


# ────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────
def main() -> None:
    if not _check_python():
        _show_python_error()
        sys.exit(1)

    if not _check_deps():
        _show_dep_error()
        sys.exit(1)

    # Importar y lanzar la ventana principal
    from app.ui.app_window import AppWindow
    app = AppWindow()
    app.run()


if __name__ == "__main__":
    main()
