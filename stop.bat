@echo off
setlocal
cd /d "%~dp0"
title Taiwan Alpha Radar - Stop (Docker)

echo ==================================================
echo   Taiwan Alpha Radar - Stop Frontend/Backend (Docker)
echo ==================================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker not found. If you started with start-local.bat, use stop-local.bat.
  pause
  exit /b 1
)

echo Stopping and removing containers ...
docker compose down
if errorlevel 1 (
  echo [ERROR] docker compose down failed. See messages above.
  pause
  exit /b 1
)

echo.
echo Stopped. Database data is kept in the pgdata volume.
echo To also wipe data, run:  docker compose down -v
echo.
pause
exit /b 0
