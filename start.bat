@echo off
rem One click without Docker: needs Python, Node.js and PostgreSQL installed
rem (docs\WINDOWS_SETUP.md Steps 1-4). Runs the one-time setup if needed, then
rem opens the backend and website in two windows and the site in your browser.
cd /d "%~dp0"
if not exist "backend\.venv" (
  echo First run: setting up the backend...
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\setup_backend.ps1"
  if errorlevel 1 ( pause & exit /b 1 )
)
start "CricLive backend" powershell -NoExit -ExecutionPolicy Bypass -File "scripts\start_backend.ps1"
start "CricLive website" powershell -NoExit -ExecutionPolicy Bypass -File "scripts\start_frontend.ps1"
echo Waiting for the website...
:wait
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://localhost:5173 -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 ( timeout /t 2 /nobreak >nul & goto wait )
start http://localhost:5173
echo CricLive is running. Close the two PowerShell windows to stop it.
