@echo off
setlocal enabledelayedexpansion
title Taiwan Alpha Radar - Stop (Local)

echo ==================================================
echo   Taiwan Alpha Radar - Stop Local Frontend/Backend
echo ==================================================
echo.
echo Stopping processes on port 8000 (backend) and 3000 (frontend) ...
echo.

set "FOUND="
for %%p in (8000 3000) do (
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p " ^| findstr LISTENING') do (
    echo Killing port %%p  PID %%a
    taskkill /F /PID %%a >nul 2>&1
    set "FOUND=1"
  )
)

if not defined FOUND (
  echo No running frontend/backend process found (maybe already stopped).
)

echo.
echo Done.
pause
exit /b 0
