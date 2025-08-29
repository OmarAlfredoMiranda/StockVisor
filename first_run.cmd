@echo off
setlocal enableextensions
title StockVisor v8 - Instalador ONECLICK

REM --- Ir al directorio del script ---
cd /d "%~dp0"

echo.
echo [1/3] Creando entorno virtual (venv)...
if not exist ".venv" (
    py -3 -m venv .venv
)
IF %ERRORLEVEL% NEQ 0 (
    echo Error creando venv. Asegurate de tener Python 3.11+ instalado y agregado al PATH.
    pause
    exit /b 1
)

echo.
echo [2/3] Activando venv...
call ".venv\Scripts\activate.bat"

echo.
echo [3/3] Instalando dependencias (esto puede tardar)...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo Hubo un problema instalando dependencias.
    echo Intenta ejecutar de nuevo este instalador.
    pause
    exit /b 1
)

echo.
echo Verificando instalacion...
py - <<PY
import flask, cv2, ultralytics, numpy
print("OK")
print("flask:", flask.__version__)
print("cv2:", cv2.__version__)
import importlib.metadata as md
print("ultralytics:", md.version("ultralytics"))
print("numpy:", numpy.__version__)
PY

echo.
echo Listo. Iniciando la app...
call run_web.cmd

endlocal
