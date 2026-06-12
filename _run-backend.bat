@echo off
cd /d "%~dp0backend"
title TAR Backend :8000

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Virtual env not found. Run start-local.bat first.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat

REM Local mode: SQLite (no Postgres). Redis falls back to disabled if absent.
set "DATABASE_URL=sqlite:///./taiwan_alpha_radar.db"
set "REDIS_URL=redis://localhost:6379/0"
set "AI_PROVIDER=mock"
set "CORS_ORIGINS=http://localhost:3000"
set "AUTO_SEED_ON_STARTUP=true"
set "ENABLE_SCHEDULER=true"

echo Starting backend (SQLite). First boot creates tables and runs analysis.
echo Wait for the line "Pipeline complete" - that means analysis is done.
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo Backend stopped.
pause
