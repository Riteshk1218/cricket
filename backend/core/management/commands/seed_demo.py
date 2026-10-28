"""Create realistic local demo data: 4 tournaments, 16 teams, users and 4 live matches.

Usage:  python manage.py seed_demo            (adds data if missing)
        python manage.py seed_demo --reset    (deletes demo data first)
All demo accounts use the password given by --password (default: Cricket@123).
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.cricket_rules import default_rules
from matches.engine import service
from matches.models import Match, ScorerAssignment
from tournaments.models import Ground, Player, Team, Tournament, TournamentRegistration
from tournaments.services import generate_league_fixtures

FIRST = ["Aarav", "Vihaan", "Aditya", "Arjun", "Sai", "Reyansh", "Krishna", "Ishaan", "Rohan", "Kabir", "Omkar",
         "Pranav", "Siddharth", "Tanmay", "Yash", "Atharva", "Shreyas", "Nikhil", "Rahul", "Kunal", "Harsh",
         "Varun", "Mihir", "Aniket", "Gaurav", "Saurabh", "Ajinkya", "Tejas", "Ketan", "Parth", "Rushikesh",
         "Sahil", "Manav", "Dhruv", "Ayaan", "Vedant", "Chinmay", "Soham", "Rajat", "Abhishek"]
LAST = ["Patil", "Kulkarni", "Deshmukh", "Joshi", "Shinde", "Pawar", "Jadhav", "Gaikwad", "More", "Chavan",
        "Sharma", "Verma", "Gupta", "Yadav", "Singh", "Mishra", "Iyer", "Nair", "Rao", "Reddy", "Bhosale",
        "Kale", "Sawant", "Naik", "Desai", "Mehta", "Shah", "Trivedi", "Pandey", "Tiwari"]

TOURNAMENTS = [
    {"name": "Pune Premier T20", "short": "PPT", "fmt": "T20", "ball": "leather", "location": "Pune",
     "ground": ("Shivaji Park Ground", "Pune"),
     "teams": [("Pune Panthers", "PNP", "#0f766e"), ("Kothrud Kings", "KTK", "#b91c1c"),
               ("Baner Blasters", "BNB", "#1d4ed8"), ("Hadapsar Hawks", "HDH", "#a16207")]},
    {"name": "Mumbai Tennis Ball League", "short": "MTBL", "fmt": "T10", "ball": "tennis", "location": "Mumbai",
     "ground": ("Azad Maidan Pitch 3", "Mumbai"),
     "teams": [("Dadar Dynamos", "DDY", "#7c3aed"), ("Andheri Avengers", "AAV", "#be185d"),
               ("Thane Tigers", "THT", "#ea580c"), ("Borivali Bulls", "BRB", "#15803d")]},
    {"name": "Nashik Box Cricket Cup", "short": "NBC", "fmt": "CUSTOM", "ball": "box", "location": "Nashik",
     "overs": 6, "ground": ("Box Arena Court 1", "Nashik"),
     "teams": [("Godavari Gladiators", "GDG", "#0369a1"), ("Panchavati Pirates", "PCP", "#4d7c0f"),
               ("Cidco Chargers", "CDC", "#c2410c"), ("Satpur Strikers", "STS", "#6d28d9")]},
    {"name": "Nagpur One Day Trophy", "short": "NODT", "fmt": "ODI", "ball": "leather", "location": "Nagpur",
     "ground": ("Civil Lines Stadium", "Nagpur"),
     "teams": [("Orange City XI", "OCX", "#f97316"), ("Sitabuldi Spartans", "SBS", "#0e7490"),
               ("Dharampeth Dragons", "DPD", "#9f1239"), ("Sadar Sultans", "SDS", "#365314")]},
]


class Command(BaseCommand):
    help = "Create demo tournaments, teams, players, users and four live matches."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data first")
        parser.add_argument("--password", default="Cricket@123")
        parser.add_argument("--no-play", action="store_true", help="Do not pre-score any balls")

    def handle(self, *args, **opts):
        rng = random.Random(2026)
        if opts["reset"]:
            names = [t["name"] for t in TOURNAMENTS]
            Match.objects.filter(tournament__name__in=names).delete()
            Tournament.objects.filter(name__in=names).delete()
            Team.objects.filter(name__in=[t[0] for x in TOURNAMENTS for t in x["teams"]]).delete()
            User.objects.filter(username__in=["superadmin", "tadmin", "scorer1", "scorer2", "scorer3", "scorer4", "viewer"]).delete()
            self.stdout.write("Removed previous demo data.")
        pw = opts["password"]
        with transaction.atomic():
            users = self._users(pw)
            live = []
            for i, spec in enumerate(TOURNAMENTS):
                live.append(self._tournament(spec, users, i, rng))
        if not opts["no_play"]:
            for i, (match, scorer) in enumerate(live):
                self._start_live(match, scorer, rng, balls=8 + i * 5)
            # Play one complete earlier fixture in the shorter formats so stats and points tables have data.
            for match, scorer in live[:3]:
                done = match.tournament.matches.exclude(pk=match.pk).order_by("match_number").first()
                if done and done.status == Match.Status.SCHEDULED:
                    done.scheduled_at = timezone.now() - timedelta(days=1)
                    done.save(update_fields=["scheduled_at"])
                    ScorerAssignment.objects.get_or_create(match=done, scorer=scorer)
                    self._start_live(done, scorer, rng, balls=10_000)
                    done.refresh_from_db()
                    self.stdout.write(f"  Completed: {done} — {getattr(done, 'result', None)}")
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write(f"  Super Admin:      superadmin / {pw}")
        self.stdout.write(f"  Tournament Admin: tadmin / {pw}")
        self.stdout.write(f"  Scorers:          scorer1..scorer4 / {pw}  (scorerN scores live match N)")
        self.stdout.write(f"  Viewer:           viewer / {pw}")
        for i, (match, scorer) in enumerate(live, start=1):
            self.stdout.write(f"  Live match {i}: #{match.pk} {match} at {match.ground} — {match.tournament.name}")

    def _users(self, pw):
        spec = [("superadmin", "super_admin", "Super Admin"), ("tadmin", "tournament_admin", "Tournament Admin"),
                ("scorer1", "scorer", "Scorer One"), ("scorer2", "scorer", "Scorer Two"),
                ("scorer3", "scorer", "Scorer Three"), ("scorer4", "scorer", "Scorer Four"),
                ("viewer", "viewer", "Demo Viewer")]
        users = {}
        for username, role, name in spec:
            u, created = User.objects.get_or_create(username=username, defaults={
                "email": f"{username}@demo.local", "role": role, "display_name": name})
            if created:
                u.set_password(pw)
                if role == "super_admin":
                    u.is_staff = True
                    u.is_superuser = True
                u.save()
            users[username] = u
        return users

    def _tournament(self, spec, users, index, rng):
        today = timezone.localdate()
        ground, _ = Ground.objects.get_or_create(name=spec["ground"][0], city=spec["ground"][1])
        extra_ground, _ = Ground.objects.get_or_create(name=f"{spec['ground'][0]} (Practice)", city=spec["ground"][1])
        t, created = Tournament.objects.get_or_create(name=spec["name"], defaults=dict(
            short_name=spec["short"], location=spec["location"], start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=20), match_format=spec["fmt"], ball_type=spec["ball"],
            rules=default_rules(spec["fmt"], spec["ball"], spec.get("overs")), created_by=users["superadmin"],
            description=f"Demo {spec['fmt']} tournament ({spec['ball']} ball) in {spec['location']}.",
        ))
        t.grounds.add(ground, extra_ground)
        t.admins.add(users["tadmin"])
        per_side = t.rules["players_per_side"]
        teams = []
        for name, short, color in spec["teams"]:
            team, made = Team.objects.get_or_create(name=name, defaults={
                "short_name": short, "primary_color": color, "city": spec["location"], "created_by": users["tadmin"]})
            if made:
                roles = ["batter"] * 5 + ["wicket_keeper"] + ["all_rounder"] * 2 + ["bowler"] * 5
                for n in range(per_side + 2):
                    Player.objects.create(
                        full_name=f"{rng.choice(FIRST)} {rng.choice(LAST)}", team=team,
                        role=roles[n % len(roles)], jersey_number=n + 1,
                        batting_style="left" if rng.random() < 0.3 else "right",
                        bowling_style=rng.choice(["Right-arm fast", "Right-arm medium", "Left-arm spin",
                                                  "Right-arm off-spin", "Leg-spin", ""]),
                        created_by=users["tadmin"])
            reg, _ = TournamentRegistration.objects.get_or_create(tournament=t, team=team)
            reg.players.set(team.players.all())
            teams.append(team)
        if not t.matches.exists():
            generate_league_fixtures(t, users["tadmin"], start_date=today, matches_per_day=1)
            # First fixture is live today at the main ground; the rest are spread over the next days.
            first = t.matches.order_by("match_number").first()
            first.scheduled_at = timezone.now() - timedelta(minutes=30)
            first.ground = ground
            first.save()
        match = t.matches.order_by("match_number").first()
        scorer = users[f"scorer{index + 1}"]
        ScorerAssignment.objects.get_or_create(match=match, scorer=scorer, defaults={"assigned_by": users["tadmin"]})
        return match, scorer

    def _start_live(self, match, scorer, rng, balls):
        match.refresh_from_db()
        if match.status != Match.Status.SCHEDULED:
            return
        per_side = match.rules["players_per_side"]
        for team in (match.team_a, match.team_b):
            players = list(team.players.order_by("jersey_number"))[:per_side]
            service.set_squad(scorer, match.pk, team.pk, [
                {"player": p.pk, "is_captain": i == 0, "is_wicket_keeper": p.role == "wicket_keeper"}
                for i, p in enumerate(players)])
        service.record_toss(scorer, match.pk, match.team_a_id, rng.choice(["bat", "bowl"]))
        from .simulate_live import Simulator

        sim = Simulator(match.pk, scorer, rng)
        sim.ensure_innings()
        for _ in range(balls):
            if not sim.step():
                break
