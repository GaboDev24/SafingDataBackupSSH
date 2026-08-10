@echo off
chcp 65001 > nul
title SafingData — Compilar Ejecutable (.exe)
cd /d "%~dp0"

echo.
echo ============================================================
echo   SAFINGDATA — Generador de Ejecutable (.exe)
echo ============================================================
echo.

where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] PyInstaller no detectado globalmente. Instalando PyInstaller...
    python -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo instalar PyInstaller.
        pause
        exit /b 1
    )
)

echo [*] Compilando ejecutable SafingData.exe con icono.ico...
pyinstaller --noconfirm SafingData.spec

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   ✓ Compilación completada con éxito.
    echo   El ejecutable se encuentra en: dist\SafingData.exe
    echo ============================================================
    echo.
) else (
    echo.
    echo ERROR: La compilación falló con código %errorlevel%.
    echo.
)

pause
