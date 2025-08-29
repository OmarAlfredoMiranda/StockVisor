@echo off
setlocal enableextensions
title StockVisor v8 - Web
cd /d "%~dp0"

if not exist ".venv" (
  echo No existe el entorno virtual. Ejecuta primero first_run.cmd
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"

REM Lanzar la app Flask
py -m web.app

endlocal
