import uuid
from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from core.cricket_rules import default_rules
from matches.engine import service
from matches.models import Match, ScorerAssignment
from tournaments.models import Ground, Player, Team, Tournament, TournamentRegistration


@pytest.fixture(autouse=True)
def _locmem_layers(settings):
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}


def make_user(username, role="viewer", password="Str0ng-pass!"):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password=password, role=role)
    return user


@pytest.fixture
def super_admin(db):
    return make_user("boss", "super_admin")


@pytest.fixture
def scorer(db):
    return make_user("scorer1", "scorer")


def make_team(name, short, n=11):
    team = Team.objects.create(name=name, short_name=short)
    for i in range(1, n + 1):
        Player.objects.create(full_name=f"{short} Player{i}", short_name=f"{short}{i}", team=team)
    return team


def make_tournament(name="Test Cup", fmt="T20", ball="leather", overs=None, **rules):
    r = default_rules(fmt, ball, overs)
    r.update(rules)
    today = date.today()
    return Tournament.objects.create(name=name, start_date=today, end_date=today + timedelta(days=10),
                                     match_format=fmt, ball_type=ball, rules=r)


def setup_match(tournament=None, scorer=None, n=11, overs=None, **rules):
    """Create a match with both squads selected, toss done (team A bats)."""
    tournament = tournament or make_tournament(overs=overs, fmt="CUSTOM" if overs else "T20", **rules)
    suffix = uuid.uuid4().hex[:4].upper()
    a = make_team(f"Alpha {suffix}", f"A{suffix[:3]}", n)
    b = make_team(f"Bravo {suffix}", f"B{suffix[:3]}", n)
    for t in (a, b):
        reg = TournamentRegistration.objects.create(tournament=tournament, team=t)
        reg.players.set(t.players.all())
    ground = Ground.objects.create(name=f"Ground {suffix}")
    match = Match.objects.create(tournament=tournament, team_a=a, team_b=b, ground=ground,
                                 scheduled_at=timezone.now(), rules=dict(tournament.rules))
    if scorer is not None:
        ScorerAssignment.objects.create(match=match, scorer=scorer)
    return match, a, b


def ready_match(scorer, n=11, overs=None, **rules):
    match, a, b = setup_match(scorer=scorer, n=n, overs=overs, **rules)
    pa = list(a.players.order_by("id"))
    pb = list(b.players.order_by("id"))
    service.set_squad(scorer, match.pk, a.pk, [{"player": p.pk} for p in pa])
    service.set_squad(scorer, match.pk, b.pk, [{"player": p.pk} for p in pb])
    service.record_toss(scorer, match.pk, a.pk, "bat")
    service.start_innings(scorer, match.pk, pa[0].pk, pa[1].pk, pb[-1].pk)
    match.refresh_from_db()
    return match, pa, pb


def ball(scorer, match, **kw):
    data = {"client_event_id": str(uuid.uuid4())}
    data.update(kw)
    return service.record_delivery(scorer, match.pk, data)


def innings(match, number=None):
    qs = match.innings.order_by("number")
    return qs.get(number=number) if number else qs.last()


@pytest.fixture
def api():
    return APIClient()


def auth(client, user):
    client.force_authenticate(user)
    return client
