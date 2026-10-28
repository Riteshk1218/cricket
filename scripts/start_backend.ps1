# Start the Django API + WebSocket server, reachable from phones on the same Wi-Fi.
$backend = Join-Path $PSScriptRoot "..\backend" | Resolve-Path
Set-Location $backend
. .\.venv\Scripts\Activate.ps1
$ip = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi*" -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress
if ($ip) { Write-Host "Phones on this Wi-Fi: website http://${ip}:5173  |  app server address http://${ip}:8000" -ForegroundColor Green }
python manage.py runserver 0.0.0.0:8000
