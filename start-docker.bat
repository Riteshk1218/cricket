@echo off
rem One click: starts the database, backend and website in Docker Desktop.
rem First start downloads and builds everything (5-10 minutes); later starts take seconds.
cd /d "%~dp0"
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running. Start Docker Desktop, wait until it says "running", then double-click this file again.
  pause
  exit /b 1
)
echo Starting CricLive... (first time takes a few minutes)
docker compose up --build -d
if errorlevel 1 (
  echo Something went wrong. See the messages above.
  pause
  exit /b 1
)
echo Waiting for the backend...
:wait
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/health/ -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 ( timeout /t 2 /nobreak >nul & goto wait )
start http://localhost:5173
echo.
echo CricLive is running:  website http://localhost:5173   (demo logins use password Cricket@123)
echo Phones on the same Wi-Fi: http://YOUR-LAPTOP-IP:5173  (find the IP with: ipconfig)
echo Stop it with stop-docker.bat. Your data is kept between runs.
pause
