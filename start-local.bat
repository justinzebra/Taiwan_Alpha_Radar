@echo off
setlocal
cd /d "%~dp0"
title Taiwan Alpha Radar - Start (Local, no Docker)

echo ==================================================
echo   Taiwan Alpha Radar - Start (Local / no Docker)
echo   Backend: Python + SQLite (no Postgres/Redis)
echo   Frontend: Next.js (requires Node 16.14+)
echo ==================================================
echo.

REM ---- Check Python ----
where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.11+ from https://www.python.org/
  pause
  exit /b 1
)

REM ---- Backend venv + deps (first run only) ----
if not exist "backend\.venv\Scripts\python.exe" (
  echo [Backend] Creating virtual env backend\.venv ...
  python -m venv backend\.venv
  if errorlevel 1 (
    echo [ERROR] Failed to create virtual env.
    pause
    exit /b 1
  )
  echo [Backend] Installing packages, first time takes 1-3 minutes ...
  backend\.venv\Scripts\python.exe -m pip install --upgrade pip
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
  if errorlevel 1 (
    echo [ERROR] Failed to install backend packages.
    pause
    exit /b 1
  )
)

echo.
echo Opening two windows for backend and frontend ...
start "" "%~dp0_run-backend.bat"
start "" "%~dp0_run-frontend.bat"

echo.
echo Waiting for backend to be ready ...
set /a tries=0
:wait
curl -s -o nul http://localhost:8000/health
if not errorlevel 1 goto ready
set /a tries+=1
if %tries% geq 60 goto opentimeout
timeout /t 2 >nul
goto wait

:ready
echo Backend ready. Opening browser ...
start "" http://localhost:3000
goto done

:opentimeout
echo Backend not responding yet. Frontend window may still be installing packages.
echo Open http://localhost:3000 manually in a moment.
start "" http://localhost:3000

:done
echo.
echo   Backend window : "TAR Backend :8000"   http://localhost:8000/docs
echo   Frontend window: "TAR Frontend :3000"  http://localhost:3000
echo   To stop: run stop-local.bat (or just close those two windows).
echo.
pause
exit /b 0
