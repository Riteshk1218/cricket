# Architecture and API reference

```
 React website (Vite, :5173) ──┐  REST /api/* (JWT)      ┌── PostgreSQL
 Flutter app (Android/iOS) ────┼──────────────────────▶ Django 5.2 + DRF ──┤
 Scorer panels (web + app) ────┘  WebSocket /ws/*        └── Channels layer (in-memory, or Redis)
```

* **backend/**: one Django project (`config`) with apps:
  * `accounts`: user model with roles (super_admin, tournament_admin, scorer, viewer), JWT
    login/refresh/logout (blacklist), registration (always viewer), favourites.
  * `tournaments`: grounds, tournaments (format and ball-type rule presets), teams, players,
    registrations, fixture generation (round robin, knockouts, semi-finals, final), and points
    table with NRR.
  * `matches`: matches, squads, scorer assignments, innings, deliveries, wickets, corrections,
    results, the scoring engine, and WebSocket consumers.
  * `stats`: player and team statistics, and leaderboards computed from deliveries.
  * `analytics`: anonymous page views and live connection tracking for the admin dashboard.
  * `core`: rules presets, audit log, error types, and the `seed_demo` and `simulate_live` commands.
* **frontend/**: React 19, React Router 7, Tailwind 4, Axios, Recharts, Lucide icons.
* **mobile/**: Flutter (Material 3, Provider). Talks to the same API and WebSockets.

## Scoring engine (matches/engine)

* **Deliveries are immutable events.** The innings state (score, batters, bowlers, overs,
  partnerships, fall of wickets, free hit, maidens, required rate, end-of-innings detection) is
  rebuilt by `replay.replay_innings()` from the ordered list of non-voided deliveries. Because
  the state is always rebuilt, **undo** voids the last event and **edit** changes an event; both
  then replay the innings and are recorded in `ScoringCorrection` with who, when and why.
* **Rules** live in a JSON dict per tournament, copied to each match when it is created
  (`core/cricket_rules.py`):
  * overs, balls per over, players per side, wide and no-ball runs, free hit after a no-ball;
  * bowler over limit and the no-consecutive-overs rule, powerplays;
  * last man stands, dismissals that are not allowed (tennis and box cricket disable LBW);
  * super overs, and whether the new batter takes strike after a catch.
* **Safety:**
  * Every scoring action locks the match row (`select_for_update`) inside a transaction, so
    actions in one match are serialized while other matches score independently.
  * `client_event_id` (UUID) makes retries idempotent.
  * `expected_sequence` rejects stale panels with HTTP 409.
  * A partial unique index guarantees one live delivery per sequence number.
* **Broadcasts** happen in `transaction.on_commit`. Each match has its own group `match_<id>`,
  and summaries go to `live_scores`. A message carries the full snapshot plus a `version`, so
  clients ignore anything older than what they already have.
* **Commentary** (EN/MR/HI) is generated only from what was recorded: runs, extras, boundary
  flag, dismissal, fielder and (optional) shot zone. If the scorer did not record a shot
  direction, the commentary does not invent one.

## WebSockets

| URL | Messages from server |
|---|---|
| `ws://<host>:8000/ws/matches/<id>/?client=web\|android\|ios` | `snapshot` (on connect / `{"type":"resync"}`), `update` (snapshot + latest ball event), `viewers` (count), `pong` |
| `ws://<host>:8000/ws/live/` | `summary` (compact match card) for any match that changes |

Clients send `{"type":"ping"}` every ~25 s; this also refreshes the live-connection heartbeat
used for "connected viewers now".

## REST API (all under `/api/`)

Auth: `POST auth/login/` → `{access, refresh, user}`; send `Authorization: Bearer <access>`.
`POST auth/refresh/`, `POST auth/logout/` (blacklists the refresh token), `POST auth/register/`,
`GET/PATCH auth/me/`.

| Resource | Endpoints |
|---|---|
| Health | `GET health/` |
| Users (super admin; tournament admins can list scorers) | `users/`, `users/<id>/` (delete = deactivate) |
| Favourites | `favorites/` |
| Grounds | `grounds/` |
| Tournaments | `tournaments/` (`?managed=1`), `tournaments/<id>/`, `…/registrations/`, `…/generate_fixtures/`, `…/generate_knockouts/`, `…/points_table/`, `…/recalculate/` |
| Teams and players | `teams/`, `teams/<id>/players/`, `players/` (`?team=`, `?search=`), `registrations/` |
| Matches | `matches/` (`?state=live\|upcoming\|completed`, `?tournament=`, `?team=`, `?assigned=1`), `matches/<id>/`, `…/live/` (full snapshot), `…/commentary/`, `…/deliveries/`, `…/corrections/`, `…/scorers/`, `…/permissions_info/` |
| Scoring (assigned scorer, tournament admin or super admin) | `POST matches/<id>/score/` + `squad`, `toss`, `start-innings`, `delivery`, `bowler`, `batter`, `swap-strike`, `retire`, `undo`, `edit/<delivery_id>`, `end-innings`, `pause`, `resume`, `revise`, `finish` |
| Stats | `stats/players/<id>/`, `stats/teams/<id>/`, `stats/leaderboards/` (`?tournament=`) |
| Analytics | `POST analytics/track/` (anonymous), `GET analytics/dashboard/` (admins) |
| Audit | `GET audit/` (super admin) |

Example delivery:

```json
POST /api/matches/1/score/delivery/
{"client_event_id": "4a0c…", "expected_sequence": 27, "runs_bat": 4}
{"client_event_id": "…", "expected_sequence": 28, "extra_type": "noball", "runs_bat": 1}
{"client_event_id": "…", "expected_sequence": 29, "wicket": {"kind": "caught", "fielder": 51}}
```

## Analytics privacy

Page views store a daily SHA-256 hash of a random visitor id (kept in the browser or app) with
a server salt. IP addresses and raw ids are never stored. The dashboard keeps these metrics
separate: **current connections** (open WebSockets with a recent heartbeat), **unique
visitors** (distinct hashes per day), and **page views** (every view).
