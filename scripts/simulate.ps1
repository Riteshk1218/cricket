# Simulate scorers in all live matches (start the backend first).
# Optional: .\simulate.ps1 -Interval 2
param([double]$Interval = 3)
$backend = Join-Path $PSScriptRoot "..\backend" | Resolve-Path
Set-Location $backend
. .\.venv\Scripts\Activate.ps1
python manage.py simulate_live --interval $Interval
