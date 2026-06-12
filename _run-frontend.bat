@echo off
cd /d "%~dp0frontend"
title TAR Frontend :3000

REM ---- Check Node version (Next.js 13.5 needs 16.14+) ----
where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js not found. Install Node 16.14+ from https://nodejs.org/
  echo         Or use the Docker launcher start.bat instead.
  pause
  exit /b 1
)

set "NODEMAJ="
for /f "tokens=1 delims=." %%v in ('node -v 2^>nul') do set "NODEMAJ=%%v"
set "NODEMAJ=%NODEMAJ:v=%"

if "%NODEMAJ%"=="" (
  echo [ERROR] Could not read Node version.
  pause
  exit /b 1
)
if %NODEMAJ% LSS 16 (
  echo [ERROR] Detected Node v%NODEMAJ%, but this project needs Node 16.14 or newer.
  echo         Please upgrade Node from https://nodejs.org/ or use Docker start.bat.
  pause
  exit /b 1
)

if not exist "node_modules" (
  echo Installing frontend packages, first time takes 1-3 minutes ...
  call npm install --legacy-peer-deps
  if errorlevel 1 (
    echo [ERROR] Failed to install frontend packages.
    pause
    exit /b 1
  )
)

set "NEXT_PUBLIC_API_URL=http://localhost:8000/api"
echo Starting frontend dev server at http://localhost:3000 ...
echo.
call npm run dev

echo.
echo Frontend stopped.
pause
