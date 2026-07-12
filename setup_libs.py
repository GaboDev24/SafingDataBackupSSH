"""
SafingData — Script de instalación de dependencias en libs/.
Descarga paramiko y sus deps en la carpeta libs/ del pendrive.
Solo necesita ejecutarse una vez con conexión a internet.
"""

import sys
import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
LIBS_DIR = BASE_DIR / "libs"


def print_header() -> None:
    print()
    print("=" * 60)
    print("  SAFINGDATA — Instalación de dependencias")
    print("=" * 60)
    print()


def check_pip() -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def install_deps() -> bool:
    """Instala las dependencias en la carpeta libs/ del pendrive."""
    LIBS_DIR.mkdir(parents=True, exist_ok=True)

    packages = [
        "paramiko>=3.4.0",
        "bcrypt>=4.0.0",
        "cryptography>=41.0.0",
        "pynacl>=1.5.0",
        "cffi>=1.16.0",
    ]

    print(f"Instalando en: {LIBS_DIR}")
    print()

    for pkg in packages:
        print(f"  Instalando {pkg}...")
        result = subprocess.run(
            [
                sys.executable, "-m", "pip", "install",
                "--target", str(LIBS_DIR),
                "--no-user",
                "--quiet",
                pkg,
            ],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"  ✗ Error instalando {pkg}")
            return False
        print(f"  ✓ {pkg.split('>=')[0]} instalado")

    return True


def verify_install() -> bool:
    """Verifica que paramiko se pueda importar desde libs/."""
    sys.path.insert(0, str(LIBS_DIR))
    try:
        import paramiko  # noqa: F401
        print()
        print("  ✓ Verificación exitosa: paramiko disponible")
        return True
    except ImportError as e:
        print(f"  ✗ Error de verificación: {e}")
        return False


def main() -> None:
    print_header()
    print(f"Python: {sys.version}")
    print(f"Directorio libs: {LIBS_DIR}")
    print()

    if not check_pip():
        print("ERROR: pip no está disponible.")
        print("Instala pip primero: https://pip.pypa.io/en/stable/installation/")
        sys.exit(1)

    print("Descargando dependencias (requiere internet)...")
    print()

    ok = install_deps()
    if not ok:
        print()
        print("ERROR: Falló la instalación de algunas dependencias.")
        print("Revisa tu conexión a internet e intenta nuevamente.")
        sys.exit(1)

    ok = verify_install()
    if not ok:
        print()
        print("ERROR: La instalación falló la verificación.")
        sys.exit(1)

    print()
    print("=" * 60)
    print("  ✓ Instalación completada exitosamente.")
    print("  Ahora puedes ejecutar SafingData con run.bat o run.sh")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
    input("Presiona Enter para cerrar...")
