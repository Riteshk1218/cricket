"""Tournament operations: fixtures, points tables, net run rate and playoffs."""
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from core.exceptions import ScoringError

from .models import PointsTableEntry, Tournament, TournamentRegistration


def round_robin_pairs(team_ids, double=False):
    """Circle-method round robin. Returns a list of rounds, each a list of (home, away)."""
    teams = list(team_ids)
    if len(teams) < 2:
        return []
    if len(teams) % 2:
        teams.append(None)  # bye
    n = len(teams)
    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a, b = teams[i], teams[n - 1 - i]
            if a is not None and b is not None:
                pairs.append((a, b) if r % 2 == 0 else (b, a))
        rounds.append(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    if double:
        rounds += [[(b, a) for a, b in rnd] for rnd in rounds]
    return rounds


def _schedule_slots(tournament, start_date, matches_per_day, first_start, slot_hours, grounds):
    """Infinite generator of (datetime, ground) slots."""
    tz = timezone.get_current_timezone()
    day = start_date
    while True:
        for slot in range(matches_per_day):
            ground = grounds[slot % len(grounds)] if grounds else None
            start = datetime.combine(day, first_start) + timedelta(hours=slot_hours * (slot // max(1, len(grounds) or 1)))
            yield timezone.make_aware(start, tz), ground
        day += timedelta(days=1)


@transaction.atomic
def generate_league_fixtures(tournament, user, start_date=None, matches_per_day=4, first_start=time(9, 0),
                             slot_hours=3, double_round=False, replace=False):
    from matches.models import Match

    existing = tournament.matches.filter(stage=Match.Stage.LEAGUE)
    if existing.exists():
        if not replace:
            raise ScoringError("League fixtures already exist. Pass replace=true to regenerate.", "fixtures_exist")
        if existing.exclude(status=Match.Status.SCHEDULED).exists():
            raise ScoringError("Cannot regenerate: some league matches have already started.", "started")
        existing.delete()
    regs = list(tournament.registrations.select_related("team"))
    if len(regs) < 2:
        raise ScoringError("Register at least two teams first.", "not_enough_teams")
    groups = {}
    for reg in regs:
        groups.setdefault(reg.group or "A", []).append(reg.team_id)
    grounds = list(tournament.grounds.all())
    slots = _schedule_slots(tournament, start_date or tournament.start_date, matches_per_day, first_start,
                            slot_hours, grounds)
    # Interleave groups round by round so each group progresses evenly.
    group_rounds = {g: round_robin_pairs(ids, double_round) for g, ids in sorted(groups.items())}
    max_rounds = max(len(r) for r in group_rounds.values())
    number = (tournament.matches.order_by("-match_number").values_list("match_number", flat=True).first() or 0)
    created = []
    for r in range(max_rounds):
        for g, rounds in group_rounds.items():
            if r >= len(rounds):
                continue
            for a, b in rounds[r]:
                when, ground = next(slots)
                number += 1
                created.append(Match(
                    tournament=tournament, match_number=number, stage=Match.Stage.LEAGUE, group=g,
                    team_a_id=a, team_b_id=b, ground=ground, scheduled_at=when, rules=dict(tournament.rules),
                    created_by=user,
                ))
    Match.objects.bulk_create(created)
    recompute_points_table(tournament)
    return created


@transaction.atomic
def generate_knockout_round(tournament, user, start_at=None):
    """Create the next knockout round.

    * Knockout tournaments: round 1 pairs seeds 1 v N, 2 v N-1, ...; later rounds pair winners in order.
    * League tournaments: semi-finals (1st v 4th, 2nd v 3rd, or A1 v B2 / B1 v A2 with two groups),
      then the final; or a direct final when playoff_teams is 2.
    """
    from matches.models import Match

    matches = tournament.matches
    if matches.filter(stage=Match.Stage.FINAL).exists():
        raise ScoringError("The final has already been scheduled.", "final_exists")
    grounds = list(tournament.grounds.all())
    ground = grounds[0] if grounds else None
    last_match = matches.order_by("-scheduled_at").first()
    when = start_at or ((last_match.scheduled_at + timedelta(days=1)) if last_match else
                        timezone.make_aware(datetime.combine(tournament.start_date, time(9, 0))))
    number = (matches.order_by("-match_number").values_list("match_number", flat=True).first() or 0)

    def make(a, b, stage, rnd, offset=0):
        nonlocal number
        number += 1
        return Match.objects.create(
            tournament=tournament, match_number=number, stage=stage, knockout_round=rnd, team_a_id=a, team_b_id=b,
            ground=grounds[offset % len(grounds)] if grounds else ground,
            scheduled_at=when + timedelta(hours=3 * (offset // max(1, len(grounds) or 1))),
            rules=dict(tournament.rules), created_by=user,
        )

    def winners_of(qs):
        rows = list(qs.order_by("match_number"))
        if not rows or any(m.status not in Match.FINISHED_STATUSES for m in rows):
            raise ScoringError("All matches of the previous round must be finished.", "round_incomplete")
        out = []
        for m in rows:
            res = getattr(m, "result", None)
            if res is None or res.winner_id is None:
                raise ScoringError(f"Match {m.match_number} has no winner. Record a winner (super over or award).",
                                   "no_winner")
            out.append(res.winner_id)
        return out

    if tournament.kind == Tournament.Kind.KNOCKOUT:
        ko = matches.filter(knockout_round__isnull=False)
        if not ko.exists():
            regs = list(tournament.registrations.order_by("seed", "id"))
            n = len(regs)
            if n < 2 or n & (n - 1):
                raise ScoringError("A knockout draw needs 2, 4, 8 or 16 registered teams.", "bracket_size")
            ids = [r.team_id for r in regs]
            pairs = [(ids[i], ids[n - 1 - i]) for i in range(n // 2)]
            stage = Match.Stage.FINAL if n == 2 else Match.Stage.SEMI_FINAL if n == 4 else \
                Match.Stage.QUARTER_FINAL if n == 8 else Match.Stage.KNOCKOUT
            return [make(a, b, stage, 1, i) for i, (a, b) in enumerate(pairs)]
        rnd = ko.order_by("-knockout_round").first().knockout_round
        winners = winners_of(ko.filter(knockout_round=rnd))
        pairs = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
        stage = Match.Stage.FINAL if len(pairs) == 1 else Match.Stage.SEMI_FINAL if len(pairs) == 2 else \
            Match.Stage.QUARTER_FINAL if len(pairs) == 4 else Match.Stage.KNOCKOUT
        return [make(a, b, stage, rnd + 1, i) for i, (a, b) in enumerate(pairs)]

    # League with playoffs
    league = matches.filter(stage=Match.Stage.LEAGUE)
    semis = matches.filter(stage=Match.Stage.SEMI_FINAL)
    if semis.exists():
        w = winners_of(semis)
        return [make(w[0], w[1], Match.Stage.FINAL, 2)]
    if league.exclude(status__in=Match.FINISHED_STATUSES).exists():
        raise ScoringError("Finish all league matches before generating playoffs.", "league_incomplete")
    recompute_points_table(tournament)
    table = list(tournament.points_table.order_by("group", "position"))
    groups = sorted({row.group for row in table})
    if tournament.playoff_teams == 0:
        raise ScoringError("This tournament has no playoffs.", "no_playoffs")
    if tournament.playoff_teams == 2:
        overall = sorted(table, key=_rank_key)
        if len(overall) < 2:
            raise ScoringError("Not enough teams for a final.", "not_enough_teams")
        return [make(overall[0].team_id, overall[1].team_id, Match.Stage.FINAL, 1)]
    if len(groups) == 2:
        a = [r for r in table if r.group == groups[0]]
        b = [r for r in table if r.group == groups[1]]
        if len(a) < 2 or len(b) < 2:
            raise ScoringError("Each group needs at least two teams for semi-finals.", "not_enough_teams")
        pairs = [(a[0].team_id, b[1].team_id), (b[0].team_id, a[1].team_id)]
    else:
        overall = sorted(table, key=_rank_key)
        if len(overall) < 4:
            raise ScoringError("Semi-finals need at least four teams.", "not_enough_teams")
        pairs = [(overall[0].team_id, overall[3].team_id), (overall[1].team_id, overall[2].team_id)]
    return [make(x, y, Match.Stage.SEMI_FINAL, 1, i) for i, (x, y) in enumerate(pairs)]


def _rank_key(row):
    return (-row.points, -row.won, -row.net_run_rate, row.team.name)


def _innings_balls_for_nrr(innings, bpo):
    """Balls counted for NRR: an all-out side is charged its full quota of overs."""
    if innings.end_reason == "all_out":
        return innings.max_overs * bpo
    return innings.legal_balls


@transaction.atomic
def recompute_points_table(tournament):
    from matches.models import Match, MatchResult

    regs = list(TournamentRegistration.objects.filter(tournament=tournament).select_related("team"))
    rows = {reg.team_id: dict(group=reg.group or "A", played=0, won=0, lost=0, tied=0, no_result=0, points=0,
                              runs_for=0, balls_faced=0, runs_against=0, balls_bowled=0) for reg in regs}
    league = (Match.objects.filter(tournament=tournament, stage=Match.Stage.LEAGUE, status__in=Match.FINISHED_STATUSES)
              .select_related("result").prefetch_related("innings"))
    for m in league:
        res = getattr(m, "result", None)
        if res is None:
            continue
        a, b = m.team_a_id, m.team_b_id
        if a not in rows or b not in rows:
            continue
        for t in (a, b):
            rows[t]["played"] += 1
        if res.kind in (MatchResult.Kind.NO_RESULT, MatchResult.Kind.ABANDONED):
            for t in (a, b):
                rows[t]["no_result"] += 1
                rows[t]["points"] += tournament.points_no_result
            continue
        if res.kind == MatchResult.Kind.TIE:
            for t in (a, b):
                rows[t]["tied"] += 1
                rows[t]["points"] += tournament.points_tie
        elif res.winner_id:
            loser = b if res.winner_id == a else a
            rows[res.winner_id]["won"] += 1
            rows[res.winner_id]["points"] += tournament.points_win
            rows[loser]["lost"] += 1
            rows[loser]["points"] += tournament.points_loss
        if res.kind == MatchResult.Kind.AWARDED:
            continue
        bpo = m.rules.get("balls_per_over", 6)
        for inn in m.innings.all():
            if inn.is_super_over:
                continue
            balls = _innings_balls_for_nrr(inn, bpo)
            rows[inn.batting_team_id]["runs_for"] += inn.total_runs
            rows[inn.batting_team_id]["balls_faced"] += balls
            rows[inn.bowling_team_id]["runs_against"] += inn.total_runs
            rows[inn.bowling_team_id]["balls_bowled"] += balls
    bpo = tournament.rules.get("balls_per_over", 6)
    PointsTableEntry.objects.filter(tournament=tournament).exclude(team_id__in=rows.keys()).delete()
    entries = []
    for team_id, r in rows.items():
        nrr = Decimal("0")
        if r["balls_faced"] and r["balls_bowled"]:
            nrr = (Decimal(r["runs_for"]) * bpo / r["balls_faced"]) - (Decimal(r["runs_against"]) * bpo / r["balls_bowled"])
        r["net_run_rate"] = nrr.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        entry, _ = PointsTableEntry.objects.update_or_create(tournament=tournament, team_id=team_id, defaults=r)
        entries.append(entry)
    for group in {e.group for e in entries}:
        ordered = sorted([e for e in entries if e.group == group], key=_rank_key)
        for pos, e in enumerate(ordered, start=1):
            if e.position != pos:
                e.position = pos
                e.save(update_fields=["position"])
    return entries


def on_match_result_changed(match_id):
    from matches.models import Match

    match = Match.objects.select_related("tournament").filter(pk=match_id).first()
    if match is None:
        return
    tournament = match.tournament
    if match.stage == Match.Stage.LEAGUE:
        recompute_points_table(tournament)
    if match.stage == Match.Stage.FINAL:
        res = getattr(match, "result", None)
        if match.status in Match.FINISHED_STATUSES and res is not None and res.winner_id:
            tournament.winner_id = res.winner_id
            tournament.runner_up_id = match.team_b_id if res.winner_id == match.team_a_id else match.team_a_id
            tournament.status = Tournament.Status.COMPLETED
        else:
            tournament.winner = None
            tournament.runner_up = None
            tournament.status = Tournament.Status.ONGOING
        tournament.save(update_fields=["winner", "runner_up", "status"])
    elif tournament.status == Tournament.Status.UPCOMING:
        tournament.status = Tournament.Status.ONGOING
        tournament.save(update_fields=["status"])
