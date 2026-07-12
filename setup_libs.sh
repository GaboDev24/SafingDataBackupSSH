#!/usr/bin/env bash
# SafingData — Instalar dependencias (Linux/macOS)
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================================"
echo "  SAFINGDATA — Instalacion de dependencias"
echo "============================================================"
echo ""
echo "Esto instalara las librerias necesarias en libs/"
echo "Necesitas conexion a internet."
echo ""

PYTHON=""
if command -v python3 &>/dev/null; then PYTHON="python3"; fi
if [ -z "$PYTHON" ] && command -v python &>/dev/null; then PYTHON="python"; fi

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python no encontrado."
    exit 1
fi

$PYTHON setup_libs.py
