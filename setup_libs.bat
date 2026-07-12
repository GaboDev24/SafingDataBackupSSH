@echo off
chcp 65001 > nul
title SafingData — Instalar dependencias
cd /d "%~dp0"

echo.
echo ============================================================
echo   SAFINGDATA — Instalacion de dependencias
echo ============================================================
echo.
echo Este script instalara las librerias necesarias en libs\
echo Necesitas conexion a internet.
echo.
pause

REM Buscar Python
if exist "python-embed\python.exe" (
    set PYTHON="python-embed\python.exe"
    goto :run
)
where python >nul 2>&1
if %errorlevel% == 0 ( set PYTHON=python & goto :run )
where python3 >nul 2>&1
if %errorlevel% == 0 ( set PYTHON=python3 & goto :run )

echo ERROR: Python no encontrado.
pause
exit /b 1

:run
%PYTHON% setup_libs.py
pause
