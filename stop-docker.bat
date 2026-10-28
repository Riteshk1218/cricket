@echo off
rem Stops the CricLive containers. Data is kept (use "docker compose down -v" to delete it).
cd /d "%~dp0"
docker compose down
pause
