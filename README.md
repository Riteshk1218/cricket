# CricLive: cricket live scoring system

A free, local-network cricket scoring system. Scorers record ball by ball on a phone or laptop,
and everyone on the same Wi-Fi sees the score, scorecard, commentary (English, मराठी, हिंदी) and
FOUR/SIX/WICKET animations update instantly. Up to 4 or more matches can run at the same time.
No paid services, no Docker, no cloud.

| Part | Tech | Folder |
|---|---|---|
| API + WebSockets | Django 5.2 LTS, DRF, Channels, PostgreSQL, JWT | `backend/` |
| Website, scorer panel, admin | React, Vite, Tailwind, React Router, Axios, Recharts, Lucide | `frontend/` |
| Mobile app | Flutter (Android debug APK; iOS source) | `mobile/` |
| Guides | Windows setup, iOS, architecture/API, progress report | `docs/` |
| Helper scripts | PowerShell start/setup scripts, sound generator | `scripts/` |
| Live smoke test | 4-match WebSocket check | `tests/` |

## Quick start (Windows)

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
