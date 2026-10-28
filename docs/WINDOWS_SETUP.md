# Windows setup guide (beginner friendly)

This guide runs the whole system on one Windows 10/11 laptop with free tools only:
the Django backend, the React website and the Flutter Android app, and lets phones
on the same Wi-Fi watch and score matches. No Docker or cloud services are needed.

> **Honest note:** these commands were written for Windows PowerShell, but they were
> tested on Linux, not on a Windows PC. The project code, tests and builds were checked
> on Linux (see `docs/PROGRESS_REPORT.md`). If a command fails on your PC, the
> *Troubleshooting* table at the end covers the common problems.

Open **Windows PowerShell** for all commands (Start menu → type "PowerShell").
Lines starting with `#` are comments; you don't need to type them.

---

## Step 1: Install the tools (one time)

| Tool | Where | Notes |
|---|---|---|
| Python 3.13 | https://www.python.org/downloads/windows/ | Tick **"Add python.exe to PATH"** on the first installer screen. |
| Node.js 22 LTS | https://nodejs.org | The default options are fine. |
| PostgreSQL 16 | https://www.postgresql.org/download/windows/ (EDB installer) | Remember the password you choose for the `postgres` user. Port 5432. You can skip Stack Builder. |
| Git (optional) | https://git-scm.com/download/win | Only if you get the code from GitHub. |
| Flutter SDK | https://docs.flutter.dev/get-started/install/windows/mobile | Extract to `C:\src\flutter` and add `C:\src\flutter\bin` to PATH. |
| Android Studio | https://developer.android.com/studio | Needed for the Android SDK, emulator and APK builds. |

Close and reopen PowerShell, then check:

```powershell
python --version      # Python 3.13.x
node --version        # v22.x
npm --version
flutter --version
```

## Step 2: Put the project in a folder

Copy (or `git clone`) the project to `C:\Projects\cricket-live-score`, then:

```powershell
cd C:\Projects\cricket-live-score
dir   # you should see backend, frontend, mobile, docs, scripts, tests
```

## Step 3: Allow PowerShell to run the virtual-environment script (one time)

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Answer `Y` if asked.

## Step 4: Create the database

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres
```

Type the `postgres` password, then paste these lines (choose your own password):

```sql
CREATE USER cricket WITH PASSWORD 'choose-a-local-password';
CREATE DATABASE cricket_live OWNER cricket;
\q
```

## Step 5: Create the Python virtual environment and install packages

```powershell
cd C:\Projects\cricket-live-score\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

You will see `(.venv)` at the start of the prompt. Run `.\.venv\Scripts\Activate.ps1`
again whenever you open a new PowerShell window for the backend.

## Step 6: Create the settings file

```powershell
copy ..\.env.example .env
python -c "import secrets; print(secrets.token_urlsafe(50))"
notepad .env
```

In Notepad, paste the random text after `DJANGO_SECRET_KEY=` and put the database
password from Step 4 after `POSTGRES_PASSWORD=`. Save and close. The `.env` file stays on
your laptop and is ignored by Git.

## Step 7: Create the tables

```powershell
python manage.py migrate
```

## Step 8: Load the demo data (4 live matches)

```powershell
python manage.py seed_demo
```

This creates 4 tournaments (T20, tennis-ball T10, box cricket, ODI), 16 teams with players,
fixtures, a few completed matches, and **4 live matches** with a scorer assigned to each.
All demo accounts use the password `Cricket@123`:

| Username | Role |
|---|---|
| `superadmin` | Super Admin (everything, Django admin at /admin/) |
| `tadmin` | Tournament Admin |
| `scorer1` … `scorer4` | Scorer for live match 1 … 4 |
| `viewer` | Viewer |

Run `python manage.py seed_demo --reset` later to start again from fresh demo data.
To create your own super admin instead: `python manage.py createsuperuser`.

## Step 9: Start the backend (API + WebSockets)

```powershell
python manage.py runserver 0.0.0.0:8000
```

Keep this window open. `0.0.0.0` means phones on your Wi-Fi can reach it too.
Check it in a browser: http://127.0.0.1:8000/api/health/ should show `{"status": "ok"}`.

## Step 10: Redis (optional)

You can **skip Redis**. With `REDIS_URL=` empty the backend uses an in-memory channel
layer, which is enough for 4+ simultaneous matches on one laptop as long as you run **one**
server process (the normal `runserver`).

If you later want Redis (for example to run several server processes), install either
**Memurai Developer Edition** (free, Redis-compatible Windows service, https://www.memurai.com)
or Redis inside **WSL** (`wsl --install`, then `sudo apt install redis-server` and
`sudo service redis-server start`). Then set `REDIS_URL=redis://127.0.0.1:6379/0` in
`backend\.env` and restart the server.

## Step 11: Start the website

Open a **second** PowerShell window:

```powershell
cd C:\Projects\cricket-live-score\frontend
npm install
npm run dev
```

Open http://localhost:5173. Log in as `scorer1` to score, `tadmin` or `superadmin` for the
admin pages (Dashboard, tournaments, fixtures, teams, users).

The website automatically talks to the backend on the same computer name/IP at port 8000.
Only create `frontend\.env` (from `frontend\.env.example`) if your backend is somewhere else.

## Step 12: Test live updates (WebSockets) on the laptop

1. Open http://localhost:5173 in two browser windows and open the same live match in both.
2. In window 1, log in as `scorer1`, open **Scorer** and record a ball (for example **4**).
3. Window 2 updates within a second and shows the FOUR animation.

To see all 4 matches moving at once, open a **third** PowerShell window:

```powershell
cd C:\Projects\cricket-live-score\backend
.\.venv\Scripts\Activate.ps1
python manage.py simulate_live --interval 3
```

The simulator logs in as `scorer1`–`scorer4` and sends balls to the running server, like
four scorers' phones would. Stop it with `Ctrl+C`. While it runs, check that every match
gets its own updates:

```powershell
python ..\tests\live_smoke_test.py --seconds 30
```

It prints one line per match and `PASS` at the end.

## Step 13: Find your laptop's Wi-Fi IP address

```powershell
ipconfig
```

Under **Wireless LAN adapter Wi-Fi**, note the **IPv4 Address**, for example `192.168.1.10`.
Make sure the Wi-Fi network is set to **Private**: Settings → Network & Internet → Wi-Fi →
your network → Network profile type → Private.

## Step 14: Allow phones through Windows Firewall

Open PowerShell **as Administrator** (right-click → Run as administrator):

```powershell
New-NetFirewallRule -DisplayName "CricLive dev (8000, 5173)" -Direction Inbound -Protocol TCP -LocalPort 8000,5173 -Action Allow -Profile Private
```

On a phone connected to the **same Wi-Fi**, open `http://192.168.1.10:5173` (your IP).
You can remove the rule later with
`Remove-NetFirewallRule -DisplayName "CricLive dev (8000, 5173)"`.

## Step 15: Run the Flutter app

```powershell
flutter doctor            # fix anything marked with a red X (accept licences: flutter doctor --android-licenses)
cd C:\Projects\cricket-live-score\mobile
flutter pub get
flutter devices           # shows the emulator or your phone
flutter run
```

* **Android emulator:** the app's default server is `http://10.0.2.2:8000`, which is the
  emulator's name for your laptop. It works without changes.
* **Real phone over USB:** turn on Developer options → USB debugging, connect the cable,
  then `flutter run`. In the app go to **More → Settings → Server address**, enter
  `http://192.168.1.10:8000` (your IP from Step 13) and tap **Save & Test connection**.

## Step 16: Build the debug APK and install it on phones

```powershell
cd C:\Projects\cricket-live-score\mobile
flutter build apk --debug
```

The file is `mobile\build\app\outputs\flutter-apk\app-debug.apk`. Copy it to the phone
(USB, Bluetooth or a shared folder) and open it to install (allow "Install unknown apps"
when Android asks), or install over USB with
`adb install build\app\outputs\flutter-apk\app-debug.apk`.
Open the app → **More → Settings → Server address** → `http://192.168.1.10:8000` → **Save & Test connection**.

A debug APK is for testing on your own phones only. It is not signed for the Play Store.

---

## Running the automated tests

```powershell
# Backend (needs the database from Step 4; creates a separate test database)
cd C:\Projects\cricket-live-score\backend
.\.venv\Scripts\Activate.ps1
pytest

# Website
cd ..\frontend
npm run lint
npm run build

# Mobile app
cd ..\mobile
flutter analyze
flutter test
```

The test database needs permission to be created. If `pytest` says *permission denied to
create database*, run in psql (as `postgres`): `ALTER USER cricket CREATEDB;`

## Daily start (after setup)

Three windows: `scripts\start_backend.ps1`, `scripts\start_frontend.ps1`, and optionally
`scripts\simulate.ps1` (see `scripts\` for what each does). Or type the commands from
Steps 9, 11 and 12.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` opens the Microsoft Store | Reinstall Python with "Add to PATH" ticked, or turn off the App execution alias for python in Settings → Apps → Advanced app settings. |
| `Activate.ps1 cannot be loaded` | Do Step 3. |
| `password authentication failed for user "cricket"` | The password in `backend\.env` must match Step 4. |
| `connection refused` to PostgreSQL | Start the "postgresql-x64-16" service in Services (Win+R → `services.msc`). |
| Phone cannot open the site or app shows "Cannot reach" | Same Wi-Fi? Network set to Private? Firewall rule from Step 14? Server started with `0.0.0.0:8000`? Some guest/office Wi-Fi blocks devices from talking to each other: use a phone hotspot instead. |
| Website loads but scores don't update live | Look for "Reconnecting…". Make sure the backend window is running; refresh the page. |
| Live pages don't move while `simulate_live --direct` runs | Without Redis, use the default `simulate_live` (no `--direct`), which sends balls through the server. |
| `flutter doctor` shows Android licence errors | `flutter doctor --android-licenses` and accept all. |
| App installed but stays on the loading screen | Check Settings → Server address in the app and use **Test connection**. |
