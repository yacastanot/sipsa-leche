@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Credenciales de acceso a la aplicación web
:: Cambiar antes de usar en producción
set LECHE_USER=sipsa
set LECHE_PASS=cambiar_esta_clave

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       SIPSA Leche — Pipeline mensual     ║
echo  ║   http://localhost:8001  usuario: sipsa  ║
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
