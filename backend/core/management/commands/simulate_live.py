"""Simulate scorers recording balls in several matches at once (for demos and load testing).

    python manage.py simulate_live --matches 1 2 3 4 --interval 3

By default each ball is sent to the running server's REST API, logged in as the
match's assigned scorer, exactly like a real scorer's phone. That way viewers
see live WebSocket updates even with the in-memory channel layer (no Redis),
which only reaches clients of the same process. With Redis configured you can
use --direct to call the scoring service in this process instead.
Only matches with an assigned scorer are simulated. Stop with Ctrl+C.
"""
import json
import random
import threading
import time
import urllib.error
import urllib.request
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from core.exceptions import ScoringError
from matches.engine import service
from matches.models import Innings, Match, MatchSquad

ZONES = ["cover", "mid_wicket", "point", "straight", "square_leg", "fine_leg", "third_man", "mid_off", "mid_on", ""]


class ServiceActor:
    """Calls the scoring service in this process."""

    def __init__(self, scorer):
        self.scorer = scorer

    def __call__(self, action, match_id, **data):
        if action == "start-innings":
            return service.start_innings(self.scorer, match_id, data["striker"], data.get("non_striker"), data["bowler"])
        if action == "bowler":
            return service.set_bowler(self.scorer, match_id, data["bowler"])
        if action == "batter":
            return service.set_batter(self.scorer, match_id, data["player"], data["end"])
        if action == "end-innings":
            return service.end_innings(self.scorer, match_id)
        if action == "resume":
            return service.resume_match(self.scorer, match_id)
        if action == "delivery":
            return service.record_delivery(self.scorer, match_id, data)
        raise ValueError(action)


class HttpActor:
    """Posts to the running server's API as the scorer (what the scorer panel does)."""

    def __init__(self, base_url, username, password):
        self.base = base_url.rstrip("/") + "/api"
        self.username, self.password = username, password
        self.token = None

    def _post(self, path, data, auth=True):
        req = urllib.request.Request(self.base + path, data=json.dumps(data).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        if auth:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                return json.loads(res.read() or b"null")
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and auth:
                self.token = None
            try:
                body = json.loads(exc.read())
            except ValueError:
                body = {}
            raise ScoringError(str(body.get("detail") or body or exc), body.get("code") or "http_error") from None
        except urllib.error.URLError as exc:
            raise ScoringError(f"Cannot reach {self.base}: {exc.reason}. Is runserver running?", "offline") from None

    def __call__(self, action, match_id, **data):
        if not self.token:
            self.token = self._post("/auth/login/", {"username": self.username, "password": self.password}, auth=False)["access"]
        return self._post(f"/matches/{match_id}/score/{action}/", data)


class Simulator:
    def __init__(self, match_id, scorer, rng=None, actor=None):
        self.match_id = match_id
        self.scorer = scorer
        self.rng = rng or random.Random()
        self.act = actor or ServiceActor(scorer)

    def match(self):
        return Match.objects.get(pk=self.match_id)

    def squad(self, team_id):
        return list(MatchSquad.objects.filter(match_id=self.match_id, team_id=team_id)
                    .order_by("batting_order").values_list("player_id", flat=True))

    def ensure_innings(self):
        m = self.match()
        if m.status in Match.FINISHED_STATUSES:
            return None
        if m.status == Match.Status.PAUSED:
            self.act("resume", m.pk)
            m = self.match()
        inn = m.innings.filter(status=Innings.Status.IN_PROGRESS).first()
        if inn:
            return inn
        plan = service._next_innings_plan(m)
        bat, bowl = self.squad(plan[1]), self.squad(plan[2])
        self.act("start-innings", m.pk, striker=bat[0], non_striker=bat[1] if len(bat) > 1 else None, bowler=bowl[-1])
        return m.innings.filter(status=Innings.Status.IN_PROGRESS).first()

    def step(self):
        """Record one event. Returns False when the match is finished."""
        try:
            inn = self.ensure_innings()
        except ScoringError:
            return False
        if inn is None:
            return False
        inn.refresh_from_db()
        state = service.replay(inn)
        if not inn.bowler_id:
            bowl = self.squad(inn.bowling_team_id)
            limit = inn.match.rules.get("max_overs_per_bowler") or 99
            choices = [p for p in bowl[-6:] if p != state.last_completed_over_bowler and
                       (p not in state.bowlers or state.bowlers[p].balls < limit * state.balls_per_over)]
            choices = choices or [p for p in bowl if p != state.last_completed_over_bowler]
            self.act("bowler", self.match_id, bowler=self.rng.choice(choices))
            return True
        if not inn.striker_id or (not inn.non_striker_id and not inn.match.rules.get("last_man_stands")):
            busy = {inn.striker_id, inn.non_striker_id}
            avail = [p for p in self.squad(inn.batting_team_id) if p not in busy and state.batter_is_available(p)]
            if not avail:
                self.act("end-innings", self.match_id)
                return True
            self.act("batter", self.match_id, player=avail[0], end="striker" if not inn.striker_id else "non_striker")
            return True
        r = self.rng.random()
        data = {"client_event_id": str(uuid.uuid4()), "expected_sequence": state.last_sequence + 1,
                "shot_zone": self.rng.choice(ZONES)}
        if r < 0.035:
            data["extra_type"] = "wide"
        elif r < 0.05:
            data.update(extra_type="noball", runs_bat=self.rng.choice([0, 1, 4]))
        elif r < 0.065:
            data.update(extra_type="legbye", extra_runs=1)
        elif r < 0.115 and not state.free_hit_next:
            kind = self.rng.choice(["bowled", "caught", "caught", "lbw", "caught_and_bowled", "run_out"])
            if kind in inn.match.rules.get("disallowed_dismissals", []):
                kind = "bowled"
            fielders = self.squad(inn.bowling_team_id)
            data["wicket"] = {"kind": kind, "fielder": self.rng.choice(fielders) if kind in ("caught", "run_out") else None}
        else:
            data["runs_bat"] = self.rng.choices([0, 1, 2, 3, 4, 6], weights=[35, 33, 10, 2, 13, 7])[0]
        self.act("delivery", self.match_id, **data)
        return True


class Command(BaseCommand):
    help = "Simulate live ball-by-ball scoring in several matches at the same time."

    def add_arguments(self, parser):
        parser.add_argument("--matches", nargs="*", type=int, help="Match ids (default: all live matches)")
        parser.add_argument("--interval", type=float, default=3.0, help="Seconds between balls in each match")
        parser.add_argument("--balls", type=int, default=0, help="Stop after N events per match (0 = until finished)")
        parser.add_argument("--server", default="http://127.0.0.1:8000", help="Running server to send balls to")
        parser.add_argument("--password", default="Cricket@123", help="Password of the assigned scorer accounts")
        parser.add_argument("--direct", action="store_true",
                            help="Score in this process instead of via the API (viewers only see it live with Redis)")

    def handle(self, *args, **opts):
        ids = opts["matches"] or list(Match.objects.filter(status__in=Match.LIVE_STATUSES).values_list("pk", flat=True))
        if not ids:
            self.stderr.write("No live matches. Run seed_demo first or pass --matches.")
            return
        threads = []
        for mid in ids:
            match = Match.objects.get(pk=mid)
            assignment = match.scorer_assignments.filter(is_active=True).select_related("scorer").first()
            if not assignment:
                self.stderr.write(f"Match {mid} has no scorer; skipping.")
                continue
            t = threading.Thread(target=self._run, args=(mid, assignment.scorer, opts), daemon=True)
            t.start()
            threads.append(t)
            self.stdout.write(f"Simulating match {mid}: {match} (scorer {assignment.scorer.username})")
        if opts["direct"] and not settings.REDIS_URL:
            self.stderr.write("Warning: --direct without REDIS_URL; open pages will not update until refreshed.")
        try:
            while any(t.is_alive() for t in threads):
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stdout.write("Stopped.")

    def _run(self, mid, scorer, opts):
        actor = None if opts["direct"] else HttpActor(opts["server"], scorer.username, opts["password"])
        sim = Simulator(mid, scorer, actor=actor)
        count = 0
        while True:
            close_old_connections()
            try:
                if not sim.step():
                    self.stdout.write(f"Match {mid} finished: {Match.objects.get(pk=mid).result.summary}")
                    return
            except ScoringError as exc:
                self.stderr.write(f"Match {mid}: {exc.message}")
                time.sleep(opts["interval"])
            count += 1
            if opts["balls"] and count >= opts["balls"]:
                return
            time.sleep(opts["interval"])
