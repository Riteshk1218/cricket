"""Live smoke test: watch 4 matches over WebSockets at the same time.

Run the backend (python manage.py runserver 0.0.0.0:8000) and, in a second
window, the simulator (python manage.py simulate_live --interval 1). Then:

    python tests/live_smoke_test.py --seconds 30

It opens one WebSocket per live match plus the live-scores feed and checks that
every match receives its own updates, that no message leaks into another
match's socket, that versions only go forwards and that viewer counts arrive.
Exit code 0 means all checks passed. Needs: pip install websockets
"""
import argparse
import asyncio
import json
import sys
import time
import urllib.request

import websockets


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as res:
        return json.loads(res.read())


async def watch_match(ws_base, match_id, seconds, report):
    r = report.setdefault(match_id, {"updates": 0, "leaks": 0, "backwards": 0, "viewers": None, "last_version": -1, "highlights": set()})
    async with websockets.connect(f"{ws_base}/ws/matches/{match_id}/?client=smoke") as ws:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=max(0.1, end - time.monotonic())))
            except asyncio.TimeoutError:
                break
            if msg["type"] in ("snapshot", "update"):
                snap = msg["snapshot"]
                if snap["id"] != match_id:
                    r["leaks"] += 1
                if snap["version"] < r["last_version"]:
                    r["backwards"] += 1
                r["last_version"] = max(r["last_version"], snap["version"])
                if msg["type"] == "update":
                    r["updates"] += 1
                    event = msg.get("event") or {}
                    if event.get("highlight"):  # the same ball can repeat after a bowler/batter change
                        r["highlights"].add(event["delivery_id"])
                if "viewers" in msg:
                    r["viewers"] = msg["viewers"]
            elif msg["type"] == "viewers":
                r["viewers"] = msg["count"]


async def watch_ticker(ws_base, seconds, ticker):
    async with websockets.connect(f"{ws_base}/ws/live/?client=smoke") as ws:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=max(0.1, end - time.monotonic())))
            except asyncio.TimeoutError:
                break
            if msg.get("type") == "summary":
                ticker[msg["summary"]["id"]] = ticker.get(msg["summary"]["id"], 0) + 1


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--server", default="http://127.0.0.1:8000")
    ap.add_argument("--seconds", type=int, default=30)
    args = ap.parse_args()
    ws_base = args.server.replace("http", "ws", 1)
    live = get_json(f"{args.server}/api/matches/?state=live&page_size=50")["results"]
    ids = [m["id"] for m in live]
    if not ids:
        print("No live matches. Run: python manage.py seed_demo")
        return 1
    print(f"Watching {len(ids)} live matches {ids} for {args.seconds}s ...")
    report, ticker = {}, {}
    await asyncio.gather(watch_ticker(ws_base, args.seconds, ticker),
                         *(watch_match(ws_base, mid, args.seconds, report) for mid in ids))
    ok = True
    for mid in ids:
        r = report[mid]
        status = "OK" if r["updates"] and not r["leaks"] and not r["backwards"] else "FAIL"
        ok &= status == "OK"
        print(f"  match {mid}: {r['updates']} updates, {len(r['highlights'])} 4/6/W balls, version {r['last_version']}, "
              f"viewers {r['viewers']}, leaks {r['leaks']}, out-of-order {r['backwards']} -> {status}")
    print(f"  live-scores feed: {sum(ticker.values())} summaries for matches {sorted(ticker)}")
    if not any(r["updates"] for r in report.values()):
        print("No updates arrived. Is simulate_live running?")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
