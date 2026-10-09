@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       SIPSA Leche — Pipeline mensual     ║
echo  ║          http://localhost:8001           ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Activar ambiente virtual
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo AVISO: No se encontro el ambiente virtual .venv
    echo Ejecuta primero: python -m venv .venv  ^&  pip install -e .[dev]
)

.venv\Scripts\python -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload
