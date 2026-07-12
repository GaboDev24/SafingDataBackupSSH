#!/usr/bin/env bash
# SafingData — Launcher para Linux/macOS
# Ejecutar: ./run.sh  (o doble clic en gestores de archivos que soporten scripts)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================================"
echo "  SAFINGDATA — SSH Backup System"
echo "============================================================"
echo ""

# ── Buscar Python ─────────────────────────────────────────────
PYTHON=""

# Intentar python3 primero
if command -v python3 &>/dev/null; then
    PYVER=$(python3 -c "import sys; print(sys.version_info >= (3,8))" 2>/dev/null)
    if [ "$PYVER" = "True" ]; then
        PYTHON="python3"
    fi
fi

# Fallback a python
if [ -z "$PYTHON" ] && command -v python &>/dev/null; then
    PYVER=$(python -c "import sys; print(sys.version_info >= (3,8))" 2>/dev/null)
    if [ "$PYVER" = "True" ]; then
        PYTHON="python"
    fi
fi

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.8 o superior no encontrado."
    echo ""
    echo "Instala Python con:"
    echo "  Ubuntu/Debian: sudo apt install python3"
    echo "  Fedora:        sudo dnf install python3"
    echo "  Arch:          sudo pacman -S python"
    echo ""
    read -p "Presiona Enter para cerrar..."
    exit 1
fi

echo "[*] Usando: $($PYTHON --version)"

# ── Verificar e instalar dependencias ────────────────────────
if [ ! -d "libs/paramiko" ]; then
    echo ""
    echo "[!] Dependencias no instaladas. Ejecutando setup..."
    echo ""
    $PYTHON setup_libs.py
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        echo ""
        echo "ERROR: No se pudieron instalar las dependencias."
        echo "Ejecuta ./setup_libs.sh manualmente."
        read -p "Presiona Enter para cerrar..."
        exit 1
    fi
fi

# ── Lanzar la aplicación ─────────────────────────────────────
echo "[*] Iniciando SafingData..."
echo ""
$PYTHON app/main.py
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "La aplicación terminó con código de error: $EXIT_CODE"
    read -p "Presiona Enter para cerrar..."
fi
