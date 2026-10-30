# CricLive: cricket live scoring system

A free, local-network cricket scoring system. Scorers record ball by ball on a phone or laptop,
and everyone on the same Wi-Fi sees the score, scorecard, commentary (English, मराठी, हिंदी) and
FOUR/SIX/WICKET animations update instantly. Up to 4 or more matches can run at the same time.
No paid services and no cloud. Docker is optional (one-click start below).

| Part | Tech | Folder |
|---|---|---|
| API + WebSockets | Django 5.2 LTS, DRF, Channels, PostgreSQL, JWT | `backend/` |
| Website, scorer panel, admin | React, Vite, Tailwind, React Router, Axios, Recharts, Lucide | `frontend/` |
| Mobile app | Flutter (Android debug APK; iOS source) | `mobile/` |
| Guides | Windows setup, iOS, architecture/API, progress report | `docs/` |
| Helper scripts | PowerShell start/setup scripts, sound generator | `scripts/` |
| Live smoke test | 4-match WebSocket check | `tests/` |

## One-click start

**With Docker Desktop (easiest):** install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
(free for personal use), start it, then double-click **`start-docker.bat`**. It starts PostgreSQL,
the backend (with demo data on first run) and the website, then opens http://localhost:5173.
Stop it with `stop-docker.bat`. On Mac/Linux: `docker compose up --build`.

**Without Docker:** after installing Python, Node.js and PostgreSQL and creating the database
(Windows guide Steps 1–4), double-click **`start.bat`**. The first run does the setup for you.

**Android app without installing Flutter:** every push to `main` builds the debug APK on GitHub.
On the phone, download `CricLive-debug.apk` from the repository's **Releases → android-latest** page.

Docker is optional. Everything also runs directly on Windows, as described below.

## Quick start (Windows, manual)

Full beginner steps are in **[docs/WINDOWS_SETUP.md](docs/WINDOWS_SETUP.md)**. In short:

```powershell
# backend (after creating the PostgreSQL database, see the guide)
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example .env      # then edit the secret key and DB password
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 0.0.0.0:8000

# website (new window)
cd frontend; npm install; npm run dev     # http://localhost:5173

# 4 live matches moving at once (new window, optional)
cd backend; .\.venv\Scripts\Activate.ps1; python manage.py simulate_live

# Android app
cd mobile; flutter pub get; flutter run   # or: flutter build apk --debug
```

Demo accounts (password `Cricket@123`): `superadmin`, `tadmin`, `scorer1` … `scorer4`
(one per live match), `viewer`. On a phone, use `http://<laptop-wifi-ip>:5173` for the website
and set the app's **Settings → Server address** to `http://<laptop-wifi-ip>:8000`.

## Host it online (Render, free)

`render.yaml` sets up the website, API, live scores and database on Render
in one go. Step-by-step guide: [docs/RENDER_HOSTING.md](docs/RENDER_HOSTING.md).

## Tests

```powershell
cd backend; pytest                                   # 56 tests
cd frontend; npm run lint; npm run build
cd mobile; flutter analyze; flutter test             # 7 tests
python tests/live_smoke_test.py --seconds 30         # while runserver + simulate_live run
```

## Status

See **[docs/PROGRESS_REPORT.md](docs/PROGRESS_REPORT.md)** for what was verified and what was not
(Windows commands, the APK on a real phone, and iOS have not been tested yet).

## Security notes

* Secrets come from `backend/.env` (git-ignored). `.env.example` contains placeholders only.
* With `DJANGO_DEBUG=true` the server accepts any host and CORS origin, so phones on the LAN can
  connect. This is meant for a trusted home or ground Wi-Fi, not the public internet.
* Roles are enforced on the server for every scoring and admin action. Every action is written to the audit log.

## Sounds

`scripts/generate_sounds.py` synthesizes the FOUR/SIX/WICKET sounds (original, no licensing
issues) into `mobile/assets/sounds/`. The website synthesizes the same sounds live with the Web Audio API.
