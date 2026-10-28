# Run in an Administrator PowerShell. Lets phones on a *Private* Wi-Fi reach ports 8000 and 5173.
New-NetFirewallRule -DisplayName "CricLive dev (8000, 5173)" -Direction Inbound -Protocol TCP -LocalPort 8000,5173 -Action Allow -Profile Private
