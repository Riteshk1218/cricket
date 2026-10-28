# Progress report

Date: 28 Oct 2026. Status: **all 8 phases built.** The items under *Not verified* still need
checking on a real Windows PC, Android phone and Mac.

## What was built

| Phase | Result |
|---|---|
| 1. Project, models, auth and roles | Django 5.2 LTS + DRF + PostgreSQL. Users have 4 roles, enforced on the server (`accounts/permissions.py`). JWT with refresh rotation and logout blacklist. |
| 2. Tournaments | T10, T20, ODI or custom overs; leather, tennis-ball or box cricket presets; league (groups, round robin) and knockout. Fixture generator, semi-finals and final, points table with NRR, winner and runner-up. |
| 3. Scoring engine | Ball by ball: runs, wides, no-balls (bat/bye/leg-bye runs), byes, leg byes, penalty runs, all dismissal types, run out with crossing, free hit (including carry-over), maidens, bowler limits and no consecutive overs. Also: last man stands, retirements, mid-over bowler change, undo, edit with full replay and correction history, declarations, interruptions with revised overs/target (entered manually, no DLS), ties, super overs, no result, abandoned, awarded. Transaction lock per match, idempotent event ids, 409 on stale panels. |
| 4. Realtime | Django Channels. One WebSocket group per match plus a live-scores feed, versioned snapshots, viewer counts, heartbeats and reconnect. |
| 5. Website | React/Vite/Tailwind. Live matches, match centre (scorecard, commentary, overs, charts, partnerships), tournaments, fixtures, points, leaderboards, teams, players, stats. EN/MR/HI, dark mode, FOUR/SIX/WICKET animations, original synthesized sounds with mute and volume. |
| 6. Scorer and admin | Web scorer panel (squads, toss, start innings, run pad, extras, wickets, new batter/bowler prompts, undo, edit, retire, pause/resume, revise, finish). Admin: dashboard analytics (current connections, unique visitors and page views as separate metrics), tournaments, fixtures, scorer assignment, teams/players, grounds, users, audit log. |
| 7. Flutter app | Android + iOS source. Splash, login/register, home, live/upcoming/results, match centre (live, scorecard, commentary, overs) with WebSocket, celebrations and sounds. Also tournaments (fixtures, points, leaders, teams), teams, players and stats, the scorer panel, profile, and settings (server address with connection test, language, theme, sound, volume, animations). |
| 8. Docs, demo, tests | `seed_demo` (4 tournaments, 16 teams, 4 live matches, test accounts), `simulate_live`, 4-match smoke test, Windows guide, iOS guide, architecture/API doc. |

## Verified (on Linux, in this build environment)

* **Backend tests:** `pytest`: **56 passed**. Covers:
  * the scoring engine (26), including extras, free hits, wickets, undo/edit, super over, bowler rules and NRR;
  * the API and roles (20);
  * 4-match realtime isolation, concurrent scoring threads and WebSocket viewer counts (5);
  * commentary (4);
  * a simulated full match (1).
* **4 live matches at once:** with the dev server running, `simulate_live --interval 1` scored
  matches 1, 7, 13 and 19 while `tests/live_smoke_test.py` watched all 4 sockets.
  * Each match received about 21–22 updates.
  * No messages arrived on the wrong match's socket, and none arrived out of order.
  * Viewer counts arrived, and the live-scores feed received 86 summaries. Result: **PASS**.
* **Website:**
  * `npm run build` succeeds; `npm run lint` shows 0 errors and 3 warnings (fast-refresh hints only).
  * A headless Chromium run had no JS errors. A viewer saw a SIX animation pushed over WebSocket.
  * Scorer flow checked in the browser: wide, wicket, new batter prompt, over change with bowler
    prompt, undo with confirmation, no-ball → FREE HIT, edit.
  * Admin dashboard, Marathi and dark mode render.
* **Flutter app:**
  * `flutter analyze`: no issues; `flutter test`: 7 passed.
  * The same Dart code was also compiled for the web (throwaway build, not part of the project)
    and driven in headless Chromium against the real backend, with no errors:
    * home showed 4 live matches;
    * the match centre updated live and showed the FOUR animation when a ball was scored;
    * login as `scorer1` → My scoring matches → scorer panel: run, wide, bowled wicket, automatic
      new-batter prompt, end of over, automatic bowler prompt (previous bowler excluded), undo
      with confirmation.
* **Docker one-click setup** (`docker-compose.yml`): built and started on Linux.
  * PostgreSQL, the backend and the website all came up, and demo data loaded on the first start.
  * Data was kept after a restart (demo data was not loaded again).
  * The website loaded in Chromium with no errors, showing the live matches.
  * The 4-match smoke test passed against the containers.
  * The `.bat` files themselves were not run, because no Windows machine was available.
* `pip install -r backend/requirements.txt` works in a clean virtual environment (Python 3.13).

## Not verified (could not be tested here)

* **Windows commands and PowerShell scripts** (`docs/WINDOWS_SETUP.md`, `scripts/*.ps1`): written
  for Windows but not run on Windows. No Windows machine was available.
* **Android APK:** `flutter build apk --debug` could not run, because the Android SDK download
  (dl.google.com) is blocked in this environment ("No Android SDK found"). The app has not been
  installed on a real phone or emulator, so audio playback through `audioplayers`, Android
  cleartext/LAN networking and phone layouts still need a check on a device. Do Steps 15–16 of
  the Windows guide.
* **iOS:** not built and not tested (needs macOS + Xcode). See `docs/IOS_BUILD.md`.
* **Phones over real Wi-Fi:** the LAN setup (IP, firewall, `0.0.0.0` binding) follows standard
  practice, but no physical phone was used.
* **Redis:** all tests used the in-memory channel layer. The Redis option is wired in settings
  but was not exercised.

## Known limitations

* Rain-affected matches use a **manually entered** revised overs/target. There is no DLS calculation.
* The mobile scorer panel covers live scoring. Editing an older ball, revising overs/target and
  entering a manual result are done on the website scorer panel.
* The in-memory channel layer works for one server process. Use Redis/Memurai to run several.
* The dev server (`runserver`) and debug settings are for a local network only. They are not hardened for the internet.

## How to resume

1. Follow `docs/WINDOWS_SETUP.md` on the Windows PC and run the automated tests.
2. Build the debug APK (Step 16), install it on 2 phones, set the server address, and check live
   updates, sounds and the scorer panel on the device.
3. Optional: build on a Mac using `docs/IOS_BUILD.md`.
