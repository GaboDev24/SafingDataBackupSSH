@echo off
chcp 65001 > nul
title SafingData — Launcher
cd /d "%~dp0"

echo.
echo ============================================================
echo   SAFINGDATA — SSH Backup System
echo ============================================================
echo.

REM ── Buscar Python embebido primero ───────────────────────────
if exist "python-embed\python.exe" (
    echo [*] Usando Python embebido del pendrive...
    set PYTHON="python-embed\python.exe"
    goto :run
)

REM ── Buscar Python del sistema ─────────────────────────────────
where python >nul 2>&1
if %errorlevel% == 0 (
    echo [*] Usando Python del sistema...
    set PYTHON=python
    goto :run
)

where python3 >nul 2>&1
if %errorlevel% == 0 (
    echo [*] Usando Python3 del sistema...
    set PYTHON=python3
    goto :run
)

REM ── Python no encontrado ──────────────────────────────────────
echo.
echo ERROR: Python no encontrado.
echo.
echo Opciones:
echo   1. Descarga Python desde https://www.python.org/downloads/
echo   2. O ejecuta setup_libs.bat para descargar Python embebido
echo.
pause
exit /b 1

:run
REM ── Verificar e instalar deps si no existen ───────────────────
if not exist "libs\paramiko" (
    echo.
    echo [!] Dependencias no instaladas. Ejecutando setup...
    echo.
    %PYTHON% setup_libs.py
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: No se pudieron instalar las dependencias.
        echo Ejecuta setup_libs.bat manualmente.
        pause
        exit /b 1
    )
)

REM ── Lanzar la aplicación ──────────────────────────────────────
echo [*] Iniciando SafingData...
echo.
%PYTHON% app\main.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: La aplicacion termino con error %errorlevel%.
    pause
)
