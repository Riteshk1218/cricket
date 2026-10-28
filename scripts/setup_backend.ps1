# One-time backend setup on Windows (run from the project folder or anywhere).
# Creates the virtual environment, installs packages, creates backend\.env if missing,
# runs migrations and loads the demo data. Create the PostgreSQL database first
# (docs\WINDOWS_SETUP.md, Step 4).
$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "..\backend" | Resolve-Path
Set-Location $backend

if (-not (Test-Path ".venv")) { python -m venv .venv }
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ..\.env.example .env
    $secret = python -c "import secrets; print(secrets.token_urlsafe(50))"
    (Get-Content .env) -replace '^DJANGO_SECRET_KEY=.*', "DJANGO_SECRET_KEY=$secret" | Set-Content .env
    $pw = Read-Host "PostgreSQL password for user 'cricket' (from Step 4)"
    (Get-Content .env) -replace '^POSTGRES_PASSWORD=.*', "POSTGRES_PASSWORD=$pw" | Set-Content .env
    Write-Host "Created backend\.env (local only, not committed)."
}

python manage.py migrate
python manage.py seed_demo
Write-Host "Backend ready. Start it with scripts\start_backend.ps1"
