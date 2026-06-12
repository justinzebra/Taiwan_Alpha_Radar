@echo off
cd /d "%~dp0"
title Taiwan Alpha Radar - Logs (Docker)

echo Showing backend live logs. Wait for "Pipeline complete" = analysis done.
echo Press Ctrl+C to exit.
echo.
docker compose logs -f backend
