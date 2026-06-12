@echo off
setlocal
cd /d "%~dp0"
title Taiwan Alpha Radar - Start (Docker)

echo ==================================================
echo   Taiwan Alpha Radar - Start Frontend/Backend (Docker)
echo ==================================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker not found.
  echo         Install Docker Desktop: https://www.docker.com/products/docker-desktop/
  echo         Or run start-local.bat instead (frontend needs Node 18+).
  echo.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker is installed but not running. Start Docker Desktop and retry.
  echo.
  pause
  exit /b 1
)

echo Building and starting containers: db, redis, backend, frontend ...
echo First run builds the frontend image and may take several minutes.
echo.
docker compose up -d --build
if errorlevel 1 (
  echo.
  echo [ERROR] docker compose failed. See messages above.
  pause
  exit /b 1
)

echo.
echo Waiting for backend to finish daily analysis (first run ~10-30s) ...
set /a tries=0
:wait
curl -s -o nul http://localhost:8000/health
if not errorlevel 1 goto ready
set /a tries+=1
if %tries% geq 120 goto timeout
timeout /t 2 >nul
goto wait

:ready
echo.
echo   Backend ready!
echo   Frontend : http://localhost:3000
echo   API docs : http://localhost:8000/docs
echo.
start "" http://localhost:3000
echo Opened frontend in browser. If data is missing, wait a few seconds and refresh.
echo To stop: run stop.bat   To view logs: run logs.bat
echo.
pause
exit /b 0

:timeout
echo.
echo [WARN] Backend health check timed out. Containers may still be starting.
echo        Run logs.bat to inspect, or open http://localhost:3000 later.
echo.
pause
exit /b 1
