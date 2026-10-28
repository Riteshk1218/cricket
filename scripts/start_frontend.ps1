# Start the React website (Vite dev server on port 5173, open to the local network).
$frontend = Join-Path $PSScriptRoot "..\frontend" | Resolve-Path
Set-Location $frontend
if (-not (Test-Path "node_modules")) { npm install }
npm run dev
