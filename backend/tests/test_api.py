import uuid
from datetime import date, timedelta

import pytest

from matches.engine import service
from matches.models import Match
from tournaments.models import PointsTableEntry, Team, Tournament

from .conftest import auth, ball, innings, make_team, make_user, ready_match, setup_match

pytestmark = pytest.mark.django_db


# --- Authentication -----------------------------------------------------
def test_register_login_refresh_and_me(api):
    r = api.post("/api/auth/register/", {"username": "viewer1", "email": "v@example.com", "password": "Cricket#2026",
                                          "role": "super_admin"}, format="json")
    assert r.status_code == 201
    r = api.post("/api/auth/login/", {"username": "viewer1", "password": "Cricket#2026"}, format="json")
    assert r.status_code == 200
    assert r.data["user"]["role"] == "viewer"  # self-registration can never pick a privileged role
    access, refresh = r.data["access"], r.data["refresh"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert api.get("/api/auth/me/").data["username"] == "viewer1"
    r = api.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
    assert r.status_code == 200 and "access" in r.data


def test_login_rejects_bad_password(api):
    make_user("someone")
    r = api.post("/api/auth/login/", {"username": "someone", "password": "nope"}, format="json")
    assert r.status_code == 401


def test_weak_password_rejected(api):
    r = api.post("/api/auth/register/", {"username": "x", "email": "x@example.com", "password": "12345678"}, format="json")
    assert r.status_code == 400


# --- Role permissions ---------------------------------------------------
def tournament_payload(**extra):
    today = date.today()
    data = {"name": "Monsoon Cup", "start_date": str(today), "end_date": str(today + timedelta(days=5)),
            "match_format": "T10", "ball_type": "tennis", "kind": "league"}
    data.update(extra)
    return data


def test_viewer_and_scorer_cannot_create_tournament(api):
    for role in ("viewer", "scorer"):
        auth(api, make_user(f"u_{role}", role))
        assert api.post("/api/tournaments/", tournament_payload(), format="json").status_code == 403
    api.force_authenticate(None)
    assert api.post("/api/tournaments/", tournament_payload(), format="json").status_code == 401


def test_tournament_admin_creates_and_manages_only_own(api):
    ta = make_user("ta", "tournament_admin")
    other = make_user("ta2", "tournament_admin")
    auth(api, ta)
    r = api.post("/api/tournaments/", tournament_payload(), format="json")
    assert r.status_code == 201, r.data
    tid = r.data["id"]
    t = Tournament.objects.get(pk=tid)
    assert t.rules["overs_per_innings"] == 10 and "lbw" in t.rules["disallowed_dismissals"]
    assert list(t.admins.all()) == [ta]
    auth(api, other)
    assert api.patch(f"/api/tournaments/{tid}/", {"name": "Hijack"}, format="json").status_code == 403
    auth(api, ta)
    assert api.patch(f"/api/tournaments/{tid}/", {"name": "Monsoon Cup 2026"}, format="json").status_code == 200
    # Only super admins can delete.
    assert api.delete(f"/api/tournaments/{tid}/").status_code == 403


def test_custom_overs_and_invalid_rules(api, super_admin):
    auth(api, super_admin)
    r = api.post("/api/tournaments/", tournament_payload(match_format="CUSTOM", overs=8), format="json")
    assert r.status_code == 201 and r.data["rules"]["overs_per_innings"] == 8
    r = api.post("/api/tournaments/", tournament_payload(rules={"balls_per_over": 2}), format="json")
    assert r.status_code == 400
    r = api.post("/api/tournaments/", tournament_payload(end_date="2000-01-01"), format="json")
    assert r.status_code == 400


def test_super_admin_manages_users(api, super_admin):
    auth(api, super_admin)
    r = api.post("/api/users/", {"username": "newscorer", "email": "s@example.com", "role": "scorer",
                                 "password": "Score#2026x"}, format="json")
    assert r.status_code == 201
    viewer = make_user("plain")
    auth(api, viewer)
    assert api.get("/api/users/").status_code == 403
    assert api.patch(f"/api/users/{viewer.pk}/", {"role": "super_admin"}, format="json").status_code == 403


def test_scoring_requires_assignment_via_api(api, scorer):
    match, pa, pb = ready_match(scorer)
    stranger = make_user("stranger", "scorer")
    auth(api, stranger)
    r = api.post(f"/api/matches/{match.pk}/score/delivery/", {"client_event_id": str(uuid.uuid4()), "runs_bat": 1}, format="json")
    assert r.status_code == 400 and r.data["code"] == "forbidden"
    api.force_authenticate(None)
    r = api.post(f"/api/matches/{match.pk}/score/delivery/", {"client_event_id": str(uuid.uuid4()), "runs_bat": 1}, format="json")
    assert r.status_code == 401
    auth(api, scorer)
    r = api.post(f"/api/matches/{match.pk}/score/delivery/", {"client_event_id": str(uuid.uuid4()), "runs_bat": 4,
                                                             "expected_sequence": 1}, format="json")
    assert r.status_code == 201, r.data
    snap = r.data["snapshot"]
    assert snap["current"]["score"] == "4/0" and snap["commentary"][0]["highlight"] == "four"
    assert snap["commentary"][0]["text"]["mr"].startswith("चौकार")
    assert snap["commentary"][0]["text"]["hi"].startswith("चौका")
    # Stale client gets 409.
    r = api.post(f"/api/matches/{match.pk}/score/delivery/", {"client_event_id": str(uuid.uuid4()), "runs_bat": 1,
                                                             "expected_sequence": 1}, format="json")
    assert r.status_code == 409 and r.data["current_sequence"] == 1


def test_api_validation_errors(api, scorer):
    match, pa, pb = ready_match(scorer)
    auth(api, scorer)
    r = api.post(f"/api/matches/{match.pk}/score/delivery/", {"runs_bat": 1}, format="json")
    assert r.status_code == 400 and "client_event_id" in r.data
    r = api.post(f"/api/matches/{match.pk}/score/delivery/", {"client_event_id": str(uuid.uuid4()), "runs_bat": 12}, format="json")
    assert r.status_code == 400
    r = api.post(f"/api/matches/{match.pk}/score/delivery/", {"client_event_id": str(uuid.uuid4()),
                                                             "wicket": {"kind": "teleported"}}, format="json")
    assert r.status_code == 400


# --- Tournaments, teams, fixtures --------------------------------------
def test_registration_fixtures_and_squad_selection(api, super_admin):
    auth(api, super_admin)
    t = api.post("/api/tournaments/", tournament_payload(match_format="T20", ball_type="leather"), format="json").data
    teams = [make_team(f"Team {i}", f"T{i}", 12) for i in range(4)]
    for team in teams:
        r = api.post(f"/api/tournaments/{t['id']}/registrations/", {"team": team.pk}, format="json")
        assert r.status_code == 201
    assert api.post(f"/api/tournaments/{t['id']}/registrations/", {"team": teams[0].pk}, format="json").status_code == 400
    r = api.post(f"/api/tournaments/{t['id']}/generate_fixtures/", {"matches_per_day": 2}, format="json")
    assert r.status_code == 201 and r.data["created"] == 6
    pairs = {frozenset((m.team_a_id, m.team_b_id)) for m in Match.objects.filter(tournament_id=t["id"])}
    assert len(pairs) == 6
    r = api.post(f"/api/tournaments/{t['id']}/generate_fixtures/", {}, format="json")
    assert r.status_code == 400
    match = Match.objects.filter(tournament_id=t["id"]).first()
    players = list(match.team_a.players.all())
    # 12 players exceeds the playing XI limit of 11.
    r = api.post(f"/api/matches/{match.pk}/score/squad/", {"team": match.team_a_id,
                                                         "players": [{"player": p.pk} for p in players]}, format="json")
    assert r.status_code == 400
    r = api.post(f"/api/matches/{match.pk}/score/squad/", {"team": match.team_a_id,
                                                         "players": [{"player": p.pk, "is_captain": i == 0} for i, p in enumerate(players[:11])]}, format="json")
    assert r.status_code == 200
    assert len(r.data["snapshot"]["squads"][str(match.team_a_id)]) == 11
    # Toss requires both sides.
    r = api.post(f"/api/matches/{match.pk}/score/toss/", {"winner": match.team_a_id, "decision": "bat"}, format="json")
    assert r.status_code == 400 and r.data["code"] == "no_squad"


def test_points_table_and_net_run_rate(scorer):
    match, pa, pb = ready_match(scorer, overs=2, n=5)
    t = match.tournament
    for over in range(2):
        if over:
            service.set_bowler(scorer, match.pk, pb[0].pk)
        for _ in range(6):
            ball(scorer, match, runs_bat=2)
    service.start_innings(scorer, match.pk, pb[0].pk, pb[1].pk, pa[4].pk)
    ball(scorer, match, runs_bat=0, wicket={"kind": "bowled"})
    service.set_batter(scorer, match.pk, pb[2].pk, "striker")
    for _ in range(5):
        ball(scorer, match, runs_bat=1)
    service.end_innings(scorer, match.pk)
    match.refresh_from_db()
    assert match.result.winner_id == match.team_a_id and match.result.margin == 19
    from django.db import transaction  # noqa: F401
    from tournaments.services import recompute_points_table

    recompute_points_table(t)
    a = PointsTableEntry.objects.get(tournament=t, team=match.team_a)
    b = PointsTableEntry.objects.get(tournament=t, team=match.team_b)
    assert (a.played, a.won, a.points, a.position) == (1, 1, 2, 1)
    assert (b.lost, b.points, b.position) == (1, 0, 2)
    # A: 24 in 12 balls (12.0 rpo) vs 5 conceded in 6 balls (5.0) => +7.000
    assert float(a.net_run_rate) == pytest.approx(7.0)
    assert float(b.net_run_rate) == pytest.approx(-7.0)


def test_nrr_all_out_uses_full_quota():
    from types import SimpleNamespace

    from tournaments.services import _innings_balls_for_nrr

    inn = SimpleNamespace(end_reason="all_out", max_overs=20, legal_balls=50)
    assert _innings_balls_for_nrr(inn, 6) == 120
    inn.end_reason = "overs_complete"
    assert _innings_balls_for_nrr(inn, 6) == 50


def test_round_robin_pairs_cover_every_pair_once():
    from tournaments.services import round_robin_pairs

    rounds = round_robin_pairs([1, 2, 3, 4, 5])
    games = [frozenset(p) for rnd in rounds for p in rnd]
    assert len(games) == 10 and len(set(games)) == 10
    for rnd in rounds:
        teams = [t for p in rnd for t in p]
        assert len(teams) == len(set(teams))


def test_knockout_generation_and_tournament_winner(super_admin):
    today = date.today()
    t = Tournament.objects.create(name="KO Cup", start_date=today, end_date=today, kind="knockout",
                                  match_format="CUSTOM", rules={"overs_per_innings": 1})
    from tournaments.models import TournamentRegistration
    from tournaments.services import generate_knockout_round

    teams = [make_team(f"KO {i}", f"K{i}", 5) for i in range(4)]
    for i, team in enumerate(teams):
        reg = TournamentRegistration.objects.create(tournament=t, team=team, seed=i + 1)
        reg.players.set(team.players.all())
    semis = generate_knockout_round(t, super_admin)
    assert [(m.team_a_id, m.team_b_id) for m in semis] == [(teams[0].pk, teams[3].pk), (teams[1].pk, teams[2].pk)]
    for m in semis:
        service.finish_match(super_admin, m.pk, kind="awarded", winner_id=m.team_a_id)
    final = generate_knockout_round(t, super_admin)
    assert len(final) == 1 and final[0].stage == "final"
    service.finish_match(super_admin, final[0].pk, kind="awarded", winner_id=teams[1].pk)
    from tournaments.services import on_match_result_changed

    on_match_result_changed(final[0].pk)
    t.refresh_from_db()
    assert t.winner_id == teams[1].pk and t.status == "completed" and t.runner_up_id == teams[0].pk


def test_match_lists_and_public_scorecard(api, scorer):
    match, pa, pb = ready_match(scorer)
    ball(scorer, match, runs_bat=6)
    r = api.get("/api/matches/?state=live")
    assert r.status_code == 200 and r.data["results"][0]["id"] == match.pk
    r = api.get(f"/api/matches/{match.pk}/live/")
    assert r.status_code == 200
    card = r.data["innings"][0]
    assert card["total"] == 6 and card["batting"][0]["sixes"] == 1 and card["bowling"][0]["runs"] == 6
    assert r.data["current"]["striker"]["runs"] == 6
    assert api.get(f"/api/matches/{match.pk}/commentary/").status_code == 200


def test_player_stats_and_leaderboards(api, scorer):
    match, pa, pb = ready_match(scorer)
    for r in (4, 6, 1):
        ball(scorer, match, runs_bat=r)
    ball(scorer, match, runs_bat=0, wicket={"kind": "caught", "fielder": pb[2].pk})
    r = api.get(f"/api/stats/players/{pa[0].pk}/")
    bat = r.data["stats"]["batting"]
    assert bat["runs"] == 11 and bat["balls"] == 3 and bat["fours"] == 1 and bat["sixes"] == 1
    assert bat["innings"] == 1 and bat["not_outs"] == 1
    out = api.get(f"/api/stats/players/{pa[1].pk}/").data["stats"]["batting"]
    assert out["runs"] == 0 and out["not_outs"] == 0 and out["average"] == 0.0 and out["ducks"] == 1
    bowl = api.get(f"/api/stats/players/{pb[-1].pk}/").data["stats"]["bowling"]
    assert bowl["wickets"] == 1 and bowl["runs"] == 11 and bowl["overs"] == "0.4"
    fld = api.get(f"/api/stats/players/{pb[2].pk}/").data["stats"]["fielding"]
    assert fld["catches"] == 1
    lb = api.get(f"/api/stats/leaderboards/?tournament={match.tournament_id}").data
    assert lb["most_runs"][0]["player_id"] == pa[0].pk and lb["most_sixes"][0]["value"] == 1


def test_analytics_distinguishes_metrics(api, super_admin, scorer):
    match, _, _ = ready_match(scorer)
    for visitor in ("v1", "v1", "v2"):
        assert api.post("/api/analytics/track/", {"path": f"/matches/{match.pk}", "visitor_id": visitor,
                                                  "match": match.pk}, format="json").status_code == 204
    api.post("/api/analytics/track/", {"path": "/", "visitor_id": "phone", "client": "android"}, format="json")
    from analytics.services import register_connection

    register_connection("chan-1", match.pk, "web")
    auth(api, super_admin)
    r = api.get("/api/analytics/dashboard/")
    assert r.status_code == 200
    d = r.data
    assert d["traffic"]["page_views_today"] == 4
    assert d["traffic"]["unique_visitors_today"] == 3
    assert d["traffic"]["match_views_total"] == 3
    assert d["realtime"]["current_connections"] == 1
    assert d["android"]["screen_views_today"] == 1
    assert d["totals"]["live_matches"] == 1
    from analytics.models import PageView

    assert not PageView.objects.filter(visitor_hash="v1").exists()  # raw ids are never stored
    auth(api, make_user("v", "viewer"))
    assert api.get("/api/analytics/dashboard/").status_code == 403


def test_favorites(api):
    user = make_user("fan")
    team = Team.objects.create(name="Fan Team", short_name="FAN")
    auth(api, user)
    r = api.post("/api/favorites/", {"team": team.pk}, format="json")
    assert r.status_code == 201
    assert api.post("/api/favorites/", {"team": team.pk}, format="json").status_code == 400
    assert api.post("/api/favorites/", {}, format="json").status_code == 400
    assert len(api.get("/api/favorites/").data) == 1


def test_audit_log_records_scoring(scorer):
    from core.models import AuditLog

    match, pa, pb = ready_match(scorer)
    ball(scorer, match, runs_bat=1)
    service.undo_last(scorer, match.pk)
    actions = list(AuditLog.objects.filter(match=match).values_list("action", flat=True))
    assert "scoring.delivery" in actions and "scoring.undo" in actions
