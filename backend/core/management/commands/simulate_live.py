"""Simulate scorers recording balls in several matches at once (for demos and load testing).

    python manage.py simulate_live --matches 1 2 3 4 --interval 3

Each simulated ball goes through the same transactional scoring service used by
the API, so viewers connected over WebSockets see real updates. Only matches
whose assigned scorer exists are simulated. Stop with Ctrl+C.
"""
import random
import threading
import time
import uuid

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from core.exceptions import ScoringError
from matches.engine import service
from matches.models import Innings, Match, MatchSquad

ZONES = ["cover", "mid_wicket", "point", "straight", "square_leg", "fine_leg", "third_man", "mid_off", "mid_on", ""]


class Simulator:
    def __init__(self, match_id, scorer, rng=None):
        self.match_id = match_id
        self.scorer = scorer
        self.rng = rng or random.Random()

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
            service.resume_match(self.scorer, m.pk)
            m = self.match()
        inn = m.innings.filter(status=Innings.Status.IN_PROGRESS).first()
        if inn:
            return inn
        plan = service._next_innings_plan(m)
        bat, bowl = self.squad(plan[1]), self.squad(plan[2])
        service.start_innings(self.scorer, m.pk, bat[0], bat[1] if len(bat) > 1 else None, bowl[-1])
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
            service.set_bowler(self.scorer, self.match_id, self.rng.choice(choices))
            return True
        if not inn.striker_id or (not inn.non_striker_id and not inn.match.rules.get("last_man_stands")):
            busy = {inn.striker_id, inn.non_striker_id}
            avail = [p for p in self.squad(inn.batting_team_id) if p not in busy and state.batter_is_available(p)]
            if not avail:
                service.end_innings(self.scorer, self.match_id)
                return True
            service.set_batter(self.scorer, self.match_id, avail[0], "striker" if not inn.striker_id else "non_striker")
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
        service.record_delivery(self.scorer, self.match_id, data)
        return True


class Command(BaseCommand):
    help = "Simulate live ball-by-ball scoring in several matches at the same time."

    def add_arguments(self, parser):
        parser.add_argument("--matches", nargs="*", type=int, help="Match ids (default: all live matches)")
        parser.add_argument("--interval", type=float, default=3.0, help="Seconds between balls in each match")
        parser.add_argument("--balls", type=int, default=0, help="Stop after N events per match (0 = until finished)")

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
        try:
            while any(t.is_alive() for t in threads):
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stdout.write("Stopped.")

    def _run(self, mid, scorer, opts):
        sim = Simulator(mid, scorer)
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
