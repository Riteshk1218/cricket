"""Transaction-safe scoring operations.

Every public function here:
  * runs inside ``transaction.atomic`` and locks the match row with
    ``SELECT ... FOR UPDATE`` so that two scorers can never write the same
    match concurrently (other matches are not blocked);
  * checks the caller may score this match;
  * rebuilds the innings by replay to validate the change;
  * bumps ``Match.version`` and broadcasts the new snapshot after commit.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from accounts.permissions import can_manage_match, can_score_match
from core.cricket_rules import max_wickets as rules_max_wickets
from core.exceptions import ScoringConflict, ScoringError
from core.models import audit
from tournaments.models import Player

from ..models import Delivery, Innings, Match, MatchResult, MatchSquad, ScoringCorrection, Wicket
from .replay import BOWLER_CREDITED, next_positions, replay_innings, validate_dismissal

EXTRA_TYPES = {"", "wide", "noball", "bye", "legbye", "penalty"}
AUTO_RESULT_KINDS = {MatchResult.Kind.RUNS, MatchResult.Kind.WICKETS, MatchResult.Kind.TIE, MatchResult.Kind.SUPER_OVER}


# ---------------------------------------------------------------------------
# Loading and replaying
# ---------------------------------------------------------------------------
def player_names(match):
    ids = set(MatchSquad.objects.filter(match=match).values_list("player_id", flat=True))
    ids |= set(Delivery.objects.filter(innings__match=match).values_list("striker_id", flat=True))
    ids |= set(Delivery.objects.filter(innings__match=match).values_list("bowler_id", flat=True))
    return {p.id: p.short_name or p.full_name for p in Player.objects.filter(id__in=ids)}


def active_deliveries(innings):
    return list(innings.deliveries.filter(voided=False).order_by("sequence"))


def replay(innings, names=None, deliveries=None):
    match = innings.match
    names = names if names is not None else player_names(match)
    deliveries = deliveries if deliveries is not None else active_deliveries(innings)
    wickets = list(innings.dismissals.filter(voided=False).order_by("after_sequence", "id"))
    by_delivery = {w.delivery_id: w for w in wickets if w.delivery_id}
    retirements = [w for w in wickets if not w.delivery_id]
    openers = []
    if deliveries:
        openers = [deliveries[0].striker_id, deliveries[0].non_striker_id]
    else:
        openers = [innings.striker_id, innings.non_striker_id]
    return replay_innings(
        match.rules, innings.max_overs, innings.max_wickets, innings.target, deliveries, by_delivery,
        retirements, names, initial_batters=openers,
    )


def recompute(innings, names=None):
    """Replay the innings, refresh cached totals and renumber overs. Returns the state."""
    deliveries = active_deliveries(innings)
    state = replay(innings, names, deliveries)
    changed = []
    for d in deliveries:
        over_number, ball_in_over = state.numbering[d.pk]
        if (d.over_number, d.ball_in_over) != (over_number, ball_in_over):
            d.over_number, d.ball_in_over = over_number, ball_in_over
            changed.append(d)
    if changed:
        Delivery.objects.bulk_update(changed, ["over_number", "ball_in_over"])
    innings.total_runs = state.total
    innings.wickets = state.wickets
    innings.legal_balls = state.legal_balls
    innings.extras = state.extras
    innings.save(update_fields=["total_runs", "wickets", "legal_balls", "extras"])
    return state


def _lock(match_id):
    try:
        return Match.objects.select_for_update().select_related("tournament").get(pk=match_id)
    except Match.DoesNotExist:
        raise ScoringError("Match not found.", "not_found")


def _require_scorer(user, match):
    if not can_score_match(user, match):
        raise ScoringError("You are not assigned to score this match.", "forbidden")


def _current_innings(match, lock=True):
    qs = match.innings.filter(status=Innings.Status.IN_PROGRESS).order_by("-number")
    if lock:
        qs = qs.select_for_update()
    return qs.first()


def _latest_innings(match):
    return match.innings.select_for_update().order_by("-number").first()


def _squad_ids(match, team):
    return set(MatchSquad.objects.filter(match=match, team=team).values_list("player_id", flat=True))


def _bump(match, user, action, **data):
    match.version += 1
    match.save(update_fields=["version", "status", "started_at", "paused_at", "paused_seconds", "pause_reason",
                              "status_before_pause", "completed_at", "updated_at"])
    audit(user, f"scoring.{action}", match, match=match, version=match.version, **data)
    from ..realtime import broadcast_match

    match_id, version = match.pk, match.version
    transaction.on_commit(lambda: broadcast_match(match_id, version))


def _require_live(match):
    if match.status == Match.Status.PAUSED:
        raise ScoringError("The match is paused. Resume it before scoring.", "paused")
    if match.status in Match.FINISHED_STATUSES:
        raise ScoringError("The match is already finished.", "finished")


# ---------------------------------------------------------------------------
# Pre-match
# ---------------------------------------------------------------------------
def set_squad(user, match_id, team_id, players):
    """players: list of {player, is_captain, is_wicket_keeper} in batting order."""
    with transaction.atomic():
        match = _lock(match_id)
        if not (can_manage_match(user, match) or can_score_match(user, match)):
            raise ScoringError("You cannot select the playing side for this match.", "forbidden")
        if match.status not in (Match.Status.SCHEDULED, Match.Status.TOSS):
            raise ScoringError("The playing side can only be changed before the match starts.", "started")
        if team_id not in (match.team_a_id, match.team_b_id):
            raise ScoringError("That team is not playing in this match.", "invalid_team")
        limit = match.rules["players_per_side"]
        ids = [int(p["player"]) for p in players]
        if len(ids) != len(set(ids)):
            raise ScoringError("A player is listed twice.", "duplicate_player")
        if not 2 <= len(ids) <= limit:
            raise ScoringError(f"Select between 2 and {limit} players.", "squad_size")
        reg = match.tournament.registrations.filter(team_id=team_id).first()
        allowed = set(reg.players.values_list("id", flat=True)) if reg else set()
        if not allowed:
            allowed = set(Player.objects.filter(team_id=team_id).values_list("id", flat=True))
        bad = [pid for pid in ids if pid not in allowed]
        if bad:
            raise ScoringError("Some players are not registered for this team in this tournament.", "not_registered")
        other = match.team_b_id if team_id == match.team_a_id else match.team_a_id
        if MatchSquad.objects.filter(match=match, team_id=other, player_id__in=ids).exists():
            raise ScoringError("A player cannot play for both teams.", "both_teams")
        if sum(bool(p.get("is_captain")) for p in players) > 1:
            raise ScoringError("Only one captain per team.", "captain")
        MatchSquad.objects.filter(match=match, team_id=team_id).delete()
        MatchSquad.objects.bulk_create([
            MatchSquad(match=match, team_id=team_id, player_id=int(p["player"]), batting_order=i + 1,
                       is_captain=bool(p.get("is_captain")), is_wicket_keeper=bool(p.get("is_wicket_keeper")))
            for i, p in enumerate(players)
        ])
        _bump(match, user, "squad", team=team_id, players=ids)
        return match


def record_toss(user, match_id, toss_winner_id, decision):
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        if match.status not in (Match.Status.SCHEDULED, Match.Status.TOSS):
            raise ScoringError("The toss can only be recorded before the first ball.", "started")
        if toss_winner_id not in (match.team_a_id, match.team_b_id):
            raise ScoringError("The toss winner must be one of the two teams.", "invalid_team")
        if decision not in Match.TossDecision.values:
            raise ScoringError("Toss decision must be 'bat' or 'bowl'.", "invalid")
        for team_id in (match.team_a_id, match.team_b_id):
            if not MatchSquad.objects.filter(match=match, team_id=team_id).exists():
                raise ScoringError("Select the playing side for both teams before the toss.", "no_squad")
        match.toss_winner_id = toss_winner_id
        match.toss_decision = decision
        match.status = Match.Status.TOSS
        match.save(update_fields=["toss_winner", "toss_decision"])
        _bump(match, user, "toss", winner=toss_winner_id, decision=decision)
        return match


def _next_innings_plan(match):
    """Return (number, batting_team_id, bowling_team_id, max_overs, max_wickets, target, is_super_over)."""
    rules = match.rules
    innings = list(match.innings.order_by("number"))
    n = len(innings) + 1
    if n == 1:
        if not match.toss_winner_id:
            raise ScoringError("Record the toss first.", "no_toss")
        bat_first = match.toss_winner_id if match.toss_decision == "bat" else (
            match.team_b_id if match.toss_winner_id == match.team_a_id else match.team_a_id)
        bowl_first = match.team_b_id if bat_first == match.team_a_id else match.team_a_id
        return 1, bat_first, bowl_first, rules["overs_per_innings"], None, False
    last = innings[-1]
    if last.status != Innings.Status.COMPLETED:
        raise ScoringError("The current innings has not finished.", "innings_in_progress")
    if n % 2 == 0:
        # Second innings of a pair: the other side chases.
        return n, last.bowling_team_id, last.batting_team_id, last.max_overs, last.total_runs + 1, last.is_super_over
    # A new pair starts only as a super over after a tie.
    first, second = innings[-2], innings[-1]
    if second.total_runs != first.total_runs or not rules.get("super_over_on_tie"):
        raise ScoringError("No further innings: the match result is decided.", "match_decided")
    # The side that batted second in the tied pair bats first in the super over.
    return n, second.batting_team_id, second.bowling_team_id, rules.get("super_over_overs", 1), None, True


def start_innings(user, match_id, striker_id, non_striker_id, bowler_id):
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        _require_live(match)
        if match.status == Match.Status.SCHEDULED:
            raise ScoringError("Record the toss first.", "no_toss")
        if _current_innings(match):
            raise ScoringError("An innings is already in progress.", "innings_in_progress")
        number, bat_id, bowl_id, overs, target, is_super = _next_innings_plan(match)
        bat_squad, bowl_squad = _squad_ids(match, bat_id), _squad_ids(match, bowl_id)
        last_man = match.rules.get("last_man_stands")
        if striker_id not in bat_squad or (non_striker_id is not None and non_striker_id not in bat_squad):
            raise ScoringError("Opening batters must be in the batting side.", "invalid_batter")
        if non_striker_id is None and not (last_man and len(bat_squad) == 1):
            raise ScoringError("Select both opening batters.", "invalid_batter")
        if striker_id == non_striker_id:
            raise ScoringError("Choose two different opening batters.", "same_batter")
        if bowler_id not in bowl_squad:
            raise ScoringError("The bowler must be in the fielding side.", "invalid_bowler")
        if is_super:
            wkts = match.rules.get("super_over_wickets", 2)
        else:
            wkts = rules_max_wickets(match.rules, len(bat_squad))
        innings = Innings.objects.create(
            match=match, number=number, is_super_over=is_super, batting_team_id=bat_id, bowling_team_id=bowl_id,
            max_overs=overs, max_wickets=max(1, wkts), target=target, striker_id=striker_id,
            non_striker_id=non_striker_id, bowler_id=bowler_id,
        )
        match.status = Match.Status.LIVE
        if not match.started_at:
            match.started_at = timezone.now()
        _bump(match, user, "start_innings", innings=number)
        return innings


# ---------------------------------------------------------------------------
# Ball-by-ball scoring
# ---------------------------------------------------------------------------
def _delivery_fields(rules, data):
    """Translate scorer input into stored delivery fields."""
    extra_type = data.get("extra_type") or ""
    if extra_type not in EXTRA_TYPES:
        raise ScoringError("Unknown extra type.", "invalid")
    runs_bat = int(data.get("runs_bat") or 0)
    extra_runs = int(data.get("extra_runs") or 0)
    penalty = int(data.get("penalty_runs") or 0)
    boundary = bool(data.get("boundary"))
    if not 0 <= runs_bat <= 7 or not 0 <= extra_runs <= 7 or not 0 <= penalty <= 10:
        raise ScoringError("Runs are out of range.", "invalid_runs")
    f = dict(runs_bat=0, wides=0, noballs=0, byes=0, legbyes=0, penalty_runs=penalty,
             is_boundary=boundary, is_penalty_only=False)
    if extra_type == "":
        f["runs_bat"] = runs_bat
        if extra_runs:
            raise ScoringError("Use an extra type to record extra runs.", "invalid_runs")
    elif extra_type == "wide":
        if runs_bat:
            raise ScoringError("Runs cannot be scored off the bat on a wide.", "invalid_runs")
        f["wides"] = rules.get("wide_runs", 1) + extra_runs
    elif extra_type == "noball":
        f["noballs"] = rules.get("noball_runs", 1)
        nb_kind = data.get("noball_runs_type") or "bat"
        if nb_kind == "bat":
            f["runs_bat"] = runs_bat
        elif nb_kind in ("bye", "legbye"):
            if runs_bat:
                raise ScoringError("Choose bat runs or byes on a no-ball, not both.", "invalid_runs")
            f["byes" if nb_kind == "bye" else "legbyes"] = extra_runs
        else:
            raise ScoringError("noball_runs_type must be bat, bye or legbye.", "invalid")
    elif extra_type in ("bye", "legbye"):
        if runs_bat:
            raise ScoringError("Runs cannot be credited to the batter on byes or leg byes.", "invalid_runs")
        if extra_runs < 1:
            raise ScoringError("Byes and leg byes need at least one run.", "invalid_runs")
        f["byes" if extra_type == "bye" else "legbyes"] = extra_runs
    elif extra_type == "penalty":
        f["is_penalty_only"] = True
        f["penalty_runs"] = penalty or extra_runs or 5
        f["is_boundary"] = False
    if boundary:
        scored = f["runs_bat"] or f["byes"] or f["legbyes"] or (f["wides"] - rules.get("wide_runs", 1))
        if scored not in (4, 6) or (scored == 6 and not f["runs_bat"]):
            raise ScoringError("A boundary must be 4 (or 6 off the bat).", "invalid_runs")
    elif f["runs_bat"] in (4, 6) and data.get("boundary") is None:
        f["is_boundary"] = True
    return f, extra_type


def _delivery_kind(fields):
    if fields["wides"]:
        return "wide"
    if fields["noballs"]:
        return "noball"
    return "legal"


def _validate_wicket(match, innings, rules, wicket, fields, striker_id, non_striker_id, bowler_id, is_free_hit):
    if fields["is_penalty_only"]:
        raise ScoringError("A penalty award cannot include a wicket.", "invalid")
    kind = wicket.get("kind")
    out_id = int(wicket.get("player_out") or striker_id)
    if out_id not in (striker_id, non_striker_id):
        raise ScoringError("The dismissed player must be one of the two batters.", "invalid_batter")
    validate_dismissal(rules, kind, _delivery_kind(fields), is_free_hit, out_id == striker_id)
    fielder_id = wicket.get("fielder")
    fielder_id = int(fielder_id) if fielder_id else None
    if kind == "caught_and_bowled":
        fielder_id = bowler_id
    if kind in ("caught", "stumped") and not fielder_id:
        raise ScoringError("Select the fielder for this dismissal.", "fielder_required")
    if fielder_id and fielder_id not in _squad_ids(match, innings.bowling_team_id):
        raise ScoringError("The fielder must be in the fielding side.", "invalid_fielder")
    if kind in ("bowled", "lbw", "caught", "caught_and_bowled", "stumped", "hit_wicket") and \
            (fields["runs_bat"] or fields["byes"] or fields["legbyes"]):
        raise ScoringError("No runs can be scored on this kind of dismissal.", "invalid_runs")
    return kind, out_id, fielder_id


def record_delivery(user, match_id, data):
    """Record one delivery. Returns (delivery, state, duplicate)."""
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        _require_live(match)
        cid = data.get("client_event_id")
        if cid:
            existing = Delivery.objects.filter(client_event_id=cid).select_related("innings").first()
            if existing:
                if existing.innings.match_id != match.pk or existing.voided:
                    raise ScoringError("This event id was already used.", "duplicate_event")
                return existing, recompute(existing.innings), True
        innings = _current_innings(match)
        if innings is None:
            raise ScoringError("Start an innings before recording deliveries.", "no_innings")
        rules = match.rules
        names = player_names(match)
        state = replay(innings, names)
        expected = data.get("expected_sequence")
        if expected is not None and int(expected) != state.last_sequence + 1:
            raise ScoringConflict(
                "Another update was recorded for this match. Refresh and try again.", state.last_sequence)
        if state.end_reason():
            raise ScoringError("This innings is complete.", "innings_over")
        fields, extra_type = _delivery_fields(rules, data)
        striker_id, non_striker_id, bowler_id = innings.striker_id, innings.non_striker_id, innings.bowler_id
        lone_batter = rules.get("last_man_stands") and innings.wickets == innings.max_wickets - 1
        if not striker_id or (not non_striker_id and not lone_batter):
            raise ScoringError("Select the new batter before the next ball.", "need_batter")
        if not bowler_id:
            raise ScoringError("Select the bowler for this over.", "need_bowler")
        if (state.balls_in_current_over == 0 and state.current_over_bowler is None
                and bowler_id == state.last_completed_over_bowler and not rules.get("consecutive_overs_allowed")):
            raise ScoringError("A bowler cannot bowl consecutive overs. Change the bowler.", "consecutive_overs")
        wicket_data = data.get("wicket") or None
        is_free_hit = state.free_hit_next
        crossed = data.get("batters_crossed")
        if wicket_data:
            kind, out_id, fielder_id = _validate_wicket(
                match, innings, rules, wicket_data, fields, striker_id, non_striker_id, bowler_id, is_free_hit)
        extra_kwargs = {"client_event_id": cid} if cid else {}
        delivery = Delivery.objects.create(
            innings=innings, sequence=state.last_sequence + 1,
            over_number=state.legal_balls // rules["balls_per_over"], ball_in_over=state.balls_in_current_over,
            striker_id=striker_id, non_striker_id=non_striker_id, bowler_id=bowler_id,
            is_free_hit=is_free_hit, is_wicket=bool(wicket_data), shot_zone=data.get("shot_zone") or "",
            note=(data.get("note") or "")[:200], batters_crossed=crossed if wicket_data else None,
            created_by=user, **extra_kwargs, **fields,
        )
        if wicket_data:
            Wicket.objects.create(
                innings=innings, delivery=delivery, after_sequence=delivery.sequence, kind=kind,
                player_out_id=out_id, fielder_id=fielder_id,
                bowler_id=bowler_id if kind in BOWLER_CREDITED else None,
            )
        new_state = recompute(innings, names)
        _update_positions_after(innings, rules, delivery, new_state)
        reason = new_state.end_reason()
        if reason:
            _complete_innings(match, innings, reason, user)
        innings.save()
        _bump(match, user, "delivery", innings=innings.number, sequence=delivery.sequence, extra=extra_type,
              runs=delivery.total_runs, wicket=bool(wicket_data))
        return delivery, new_state, False


def _update_positions_after(innings, rules, delivery, state):
    wicket = getattr(delivery, "wicket", None) if delivery.is_wicket else None
    if wicket is not None and wicket.voided:
        wicket = None
    legal = delivery.is_legal
    over_complete = legal and state.legal_balls % rules["balls_per_over"] == 0
    s, ns = next_positions(
        rules, delivery, wicket.kind if wicket else None, wicket.player_out_id if wicket else None,
        delivery.striker_id, delivery.non_striker_id, over_complete,
    )
    innings.striker_id, innings.non_striker_id = s, ns
    innings.bowler_id = None if over_complete else delivery.bowler_id
    # Last man stands: once one batter remains, they bat alone on strike.
    if rules.get("last_man_stands") and state.wickets == innings.max_wickets - 1:
        remaining = [p for p in (s, ns) if p]
        if len(remaining) == 1 and not _available_batters(innings, state):
            innings.striker_id, innings.non_striker_id = remaining[0], None


def _available_batters(innings, state, exclude=()):
    squad = MatchSquad.objects.filter(match=innings.match, team=innings.batting_team).order_by("batting_order")
    busy = {innings.striker_id, innings.non_striker_id, *exclude}
    return [m.player_id for m in squad if m.player_id not in busy and state.batter_is_available(m.player_id)]


def _complete_innings(match, innings, reason, user):
    innings.status = Innings.Status.COMPLETED
    innings.end_reason = reason
    innings.ended_at = timezone.now()
    innings.save()
    _sync_result(match, user)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
def _sync_result(match, user):
    """Derive the result from completed innings (or set the innings-break state)."""
    innings = list(match.innings.order_by("number"))
    existing = MatchResult.objects.filter(match=match).first()
    if existing and existing.kind not in AUTO_RESULT_KINDS:
        return existing
    if not innings or innings[-1].status != Innings.Status.COMPLETED:
        if existing:
            existing.delete()
        if match.status in Match.FINISHED_STATUSES:
            match.status = Match.Status.LIVE
            match.completed_at = None
        return None
    if len(innings) % 2 == 1:
        if existing:
            existing.delete()
        match.status = Match.Status.INNINGS_BREAK
        match.completed_at = None
        return None
    first, second = innings[-2], innings[-1]
    target = second.target or first.total_runs + 1
    super_over = second.is_super_over
    if second.total_runs >= target:
        winner = second.batting_team
        margin = second.max_wickets - second.wickets
        kind = MatchResult.Kind.SUPER_OVER if super_over else MatchResult.Kind.WICKETS
        summary = (f"{winner.name} won the super over" if super_over
                   else f"{winner.name} won by {margin} wicket{'s' if margin != 1 else ''}")
    elif second.total_runs == target - 1:
        if match.rules.get("super_over_on_tie"):
            if existing:
                existing.delete()
            match.status = Match.Status.INNINGS_BREAK
            match.completed_at = None
            return None
        winner, margin, kind = None, None, MatchResult.Kind.TIE
        summary = "Match tied"
    else:
        winner = first.batting_team
        margin = target - 1 - second.total_runs
        kind = MatchResult.Kind.SUPER_OVER if super_over else MatchResult.Kind.RUNS
        summary = (f"{winner.name} won the super over" if super_over
                   else f"{winner.name} won by {margin} run{'s' if margin != 1 else ''}")
    result, _ = MatchResult.objects.update_or_create(
        match=match, defaults=dict(kind=kind, winner=winner, margin=margin, summary=summary, submitted_by=user))
    match.status = Match.Status.COMPLETED
    match.completed_at = match.completed_at or timezone.now()
    transaction.on_commit(lambda: _after_result(match.pk))
    return result


def _after_result(match_id):
    from tournaments.services import on_match_result_changed

    on_match_result_changed(match_id)


def finish_match(user, match_id, kind=None, winner_id=None, player_of_match_id=None, summary=""):
    """Confirm or record the result. ``kind`` is needed only for no result / abandoned / awarded / tie."""
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        current = _current_innings(match)
        if kind in (None, ""):
            if current:
                raise ScoringError("The current innings is still in progress.", "innings_in_progress")
            result = _sync_result(match, user)
            if result is None:
                raise ScoringError("The result is not decided yet (innings remaining or super over pending).", "undecided")
        else:
            manual = {MatchResult.Kind.NO_RESULT, MatchResult.Kind.ABANDONED, MatchResult.Kind.AWARDED, MatchResult.Kind.TIE}
            if kind not in manual:
                raise ScoringError("Only no result, abandoned, awarded or tie can be recorded manually.", "invalid")
            winner = None
            if kind == MatchResult.Kind.AWARDED:
                if winner_id not in (match.team_a_id, match.team_b_id):
                    raise ScoringError("Choose the team the match is awarded to.", "invalid_team")
                winner = match.team_a if winner_id == match.team_a_id else match.team_b
            if current:
                current.status = Innings.Status.COMPLETED
                current.end_reason = Innings.EndReason.INTERRUPTED
                current.ended_at = timezone.now()
                current.save()
            default_summary = {
                "no_result": "No result", "abandoned": "Match abandoned", "tie": "Match tied",
                "awarded": f"Match awarded to {winner.name}" if winner else "",
            }[kind]
            result, _ = MatchResult.objects.update_or_create(match=match, defaults=dict(
                kind=kind, winner=winner, margin=None, summary=summary or default_summary, submitted_by=user))
            match.status = Match.Status.ABANDONED if kind == MatchResult.Kind.ABANDONED else Match.Status.COMPLETED
            match.completed_at = timezone.now()
            match.paused_at = None
            transaction.on_commit(lambda: _after_result(match.pk))
        if player_of_match_id:
            if player_of_match_id not in _squad_ids(match, match.team_a) | _squad_ids(match, match.team_b):
                raise ScoringError("Player of the match must have played in this match.", "invalid_player")
            result.player_of_match_id = player_of_match_id
            result.save(update_fields=["player_of_match"])
        _bump(match, user, "finish", kind=result.kind)
        return result


# ---------------------------------------------------------------------------
# Players at the crease and bowler changes
# ---------------------------------------------------------------------------
def set_bowler(user, match_id, bowler_id, mid_over=False, reason=""):
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        _require_live(match)
        innings = _current_innings(match)
        if innings is None:
            raise ScoringError("No innings in progress.", "no_innings")
        rules = match.rules
        if bowler_id not in _squad_ids(match, innings.bowling_team_id):
            raise ScoringError("The bowler must be in the fielding side.", "invalid_bowler")
        state = replay(innings)
        over_started = state.current_over_bowler is not None
        if over_started and not mid_over:
            raise ScoringError("The over is in progress. Use a mid-over change only for injury.", "over_in_progress")
        if not rules.get("consecutive_overs_allowed") and bowler_id == state.last_completed_over_bowler:
            raise ScoringError("A bowler cannot bowl consecutive overs.", "consecutive_overs")
        limit = rules.get("max_overs_per_bowler")
        if limit and not innings.is_super_over:
            line = state.bowlers.get(bowler_id)
            if line and line.balls >= limit * rules["balls_per_over"]:
                raise ScoringError(f"This bowler has already bowled the maximum {limit} overs.", "bowler_limit")
        innings.bowler_id = bowler_id
        innings.save(update_fields=["bowler"])
        _bump(match, user, "set_bowler", bowler=bowler_id, mid_over=mid_over, reason=reason)
        return innings


def set_batter(user, match_id, player_id, end="striker"):
    """Send in a new batter to a vacant end (or replace after a scorer error)."""
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        _require_live(match)
        innings = _current_innings(match)
        if innings is None:
            raise ScoringError("No innings in progress.", "no_innings")
        if end not in ("striker", "non_striker"):
            raise ScoringError("End must be 'striker' or 'non_striker'.", "invalid")
        if player_id not in _squad_ids(match, innings.batting_team_id):
            raise ScoringError("The batter must be in the batting side.", "invalid_batter")
        state = replay(innings)
        if not state.batter_is_available(player_id):
            raise ScoringError("That batter is already out.", "batter_out")
        if player_id in (innings.striker_id, innings.non_striker_id):
            raise ScoringError("That batter is already at the crease.", "already_batting")
        current = innings.striker_id if end == "striker" else innings.non_striker_id
        if current is not None:
            line = state.batters.get(current)
            if line and (line.balls or line.runs):
                raise ScoringError("That end is occupied. Use retire or undo to correct it.", "end_occupied")
        setattr(innings, f"{end}_id", player_id)
        innings.save(update_fields=[end])
        _bump(match, user, "set_batter", player=player_id, end=end)
        return innings


def swap_strike(user, match_id):
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        _require_live(match)
        innings = _current_innings(match)
        if innings is None:
            raise ScoringError("No innings in progress.", "no_innings")
        innings.striker_id, innings.non_striker_id = innings.non_striker_id, innings.striker_id
        innings.save(update_fields=["striker", "non_striker"])
        _bump(match, user, "swap_strike")
        return innings


def retire_batter(user, match_id, player_id, kind="retired_hurt"):
    if kind not in ("retired_hurt", "retired_out", "timed_out"):
        raise ScoringError("Kind must be retired_hurt, retired_out or timed_out.", "invalid")
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        _require_live(match)
        innings = _current_innings(match)
        if innings is None:
            raise ScoringError("No innings in progress.", "no_innings")
        if kind in match.rules.get("disallowed_dismissals", []):
            raise ScoringError(f"'{kind}' is not allowed under this match's playing rules.", "dismissal_disallowed")
        if player_id not in (innings.striker_id, innings.non_striker_id):
            if kind != "timed_out" or player_id not in _squad_ids(match, innings.batting_team_id):
                raise ScoringError("Only a batter at the crease can retire.", "invalid_batter")
        state = replay(innings)
        Wicket.objects.create(
            innings=innings, after_sequence=state.last_sequence, kind=kind, player_out_id=player_id,
            positions_before={"striker": innings.striker_id, "non_striker": innings.non_striker_id},
        )
        if innings.striker_id == player_id:
            innings.striker_id = None
        elif innings.non_striker_id == player_id:
            innings.non_striker_id = None
        new_state = recompute(innings)
        innings.save(update_fields=["striker", "non_striker"])
        if new_state.end_reason():
            _complete_innings(match, innings, new_state.end_reason(), user)
        _bump(match, user, "retire", player=player_id, kind=kind)
        return innings


# ---------------------------------------------------------------------------
# Corrections
# ---------------------------------------------------------------------------
def delivery_snapshot(d):
    w = getattr(d, "wicket", None) if d.is_wicket else None
    return {
        "id": d.pk, "sequence": d.sequence, "over_number": d.over_number, "ball_in_over": d.ball_in_over,
        "striker": d.striker_id, "non_striker": d.non_striker_id, "bowler": d.bowler_id,
        "runs_bat": d.runs_bat, "wides": d.wides, "noballs": d.noballs, "byes": d.byes, "legbyes": d.legbyes,
        "penalty_runs": d.penalty_runs, "is_boundary": d.is_boundary, "is_penalty_only": d.is_penalty_only,
        "is_free_hit": d.is_free_hit, "shot_zone": d.shot_zone, "note": d.note,
        "wicket": ({"kind": w.kind, "player_out": w.player_out_id, "fielder": w.fielder_id, "bowler": w.bowler_id}
                   if w and not w.voided else None),
    }


def undo_last(user, match_id, reason="", expected_sequence=None):
    """Undo the most recent scoring action in the latest innings."""
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        if match.status == Match.Status.PAUSED:
            raise ScoringError("Resume the match before correcting it.", "paused")
        existing_result = MatchResult.objects.filter(match=match).first()
        if existing_result and existing_result.kind not in AUTO_RESULT_KINDS:
            raise ScoringError("This result was recorded manually. An admin must correct it.", "manual_result")
        innings = _latest_innings(match)
        if innings is None:
            raise ScoringError("Nothing to undo.", "nothing")
        deliveries = active_deliveries(innings)
        last = deliveries[-1] if deliveries else None
        if expected_sequence is not None and int(expected_sequence) != (last.sequence if last else 0):
            raise ScoringConflict("The match changed since you loaded it. Refresh and try again.",
                                  last.sequence if last else 0)
        last_ret = innings.dismissals.filter(voided=False, delivery__isnull=True).order_by("-after_sequence", "-id").first()
        if last_ret and (last is None or last_ret.after_sequence >= last.sequence):
            last_ret.voided = True
            last_ret.save(update_fields=["voided"])
            pos = last_ret.positions_before or {}
            innings.striker_id = pos.get("striker", innings.striker_id)
            innings.non_striker_id = pos.get("non_striker", innings.non_striker_id)
            before = {"retirement": {"player": last_ret.player_out_id, "kind": last_ret.kind}}
            target_delivery = None
        elif last is not None:
            before = delivery_snapshot(last)
            last.voided = True
            last.save(update_fields=["voided"])
            Wicket.objects.filter(delivery=last).update(voided=True)
            innings.striker_id, innings.non_striker_id, innings.bowler_id = last.striker_id, last.non_striker_id, last.bowler_id
            target_delivery = last
        else:
            # Empty innings: undo the start of the innings itself.
            before = {"innings_started": innings.number}
            ScoringCorrection.objects.create(match=match, innings=None, action=ScoringCorrection.Action.UNDO,
                                             before=before, reason=reason, user=user)
            innings.delete()
            remaining = match.innings.count()
            match.status = Match.Status.TOSS if remaining == 0 else Match.Status.INNINGS_BREAK
            if remaining:
                _sync_result(match, user)
            _bump(match, user, "undo", undone="innings_start")
            return None
        if innings.status == Innings.Status.COMPLETED:
            innings.status = Innings.Status.IN_PROGRESS
            innings.end_reason = ""
            innings.ended_at = None
        innings.save()
        recompute(innings)
        _sync_result(match, user)
        if match.status in (Match.Status.INNINGS_BREAK, Match.Status.COMPLETED):
            match.status = Match.Status.LIVE
        ScoringCorrection.objects.create(match=match, innings=innings, delivery=target_delivery,
                                         action=ScoringCorrection.Action.UNDO, before=before, reason=reason, user=user)
        _bump(match, user, "undo", sequence=before.get("sequence"))
        return innings


def edit_delivery(user, match_id, delivery_id, data, reason=""):
    """Correct a previously recorded delivery and replay the innings."""
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        if match.status == Match.Status.PAUSED:
            raise ScoringError("Resume the match before correcting it.", "paused")
        try:
            d = Delivery.objects.select_for_update().select_related("innings").get(
                pk=delivery_id, innings__match=match, voided=False)
        except Delivery.DoesNotExist:
            raise ScoringError("Delivery not found in this match.", "not_found")
        innings = Innings.objects.select_for_update().get(pk=d.innings_id)
        rules = match.rules
        before = delivery_snapshot(d)
        merged = {
            "runs_bat": d.runs_bat, "extra_type": "", "extra_runs": 0, "penalty_runs": d.penalty_runs,
            "boundary": d.is_boundary,
        }
        if d.wides:
            merged.update(extra_type="wide", extra_runs=d.wides - rules.get("wide_runs", 1))
        elif d.noballs:
            nb = "bye" if d.byes else "legbye" if d.legbyes else "bat"
            merged.update(extra_type="noball", noball_runs_type=nb, extra_runs=d.byes or d.legbyes)
        elif d.byes:
            merged.update(extra_type="bye", extra_runs=d.byes)
        elif d.legbyes:
            merged.update(extra_type="legbye", extra_runs=d.legbyes)
        elif d.is_penalty_only:
            merged.update(extra_type="penalty", extra_runs=0)
        merged.update({k: v for k, v in data.items() if k in {
            "runs_bat", "extra_type", "extra_runs", "noball_runs_type", "penalty_runs", "boundary"}})
        if "runs_bat" in data and "boundary" not in data:
            merged["boundary"] = None if int(data["runs_bat"] or 0) in (4, 6) else False
        fields, _ = _delivery_fields(rules, merged)
        for key in ("striker", "non_striker", "bowler"):
            if data.get(key):
                pid = int(data[key])
                team = innings.bowling_team_id if key == "bowler" else innings.batting_team_id
                if pid not in _squad_ids(match, team):
                    raise ScoringError(f"Invalid {key} for this innings.", "invalid_player")
                setattr(d, f"{key}_id", pid)
        for k, v in fields.items():
            setattr(d, k, v)
        if "shot_zone" in data:
            d.shot_zone = data.get("shot_zone") or ""
        if "note" in data:
            d.note = (data.get("note") or "")[:200]
        existing_w = Wicket.objects.filter(delivery=d, voided=False).first()
        if "wicket" in data:
            wd = data.get("wicket")
            if wd:
                kind, out_id, fielder_id = _validate_wicket(
                    match, innings, rules, wd, fields, d.striker_id, d.non_striker_id, d.bowler_id, d.is_free_hit)
                values = dict(kind=kind, player_out_id=out_id, fielder_id=fielder_id,
                              bowler_id=d.bowler_id if kind in BOWLER_CREDITED else None)
                if existing_w:
                    for k, v in values.items():
                        setattr(existing_w, k, v)
                    existing_w.save()
                else:
                    Wicket.objects.filter(delivery=d).delete()
                    Wicket.objects.create(innings=innings, delivery=d, after_sequence=d.sequence, **values)
                d.is_wicket = True
                d.batters_crossed = data.get("batters_crossed")
            else:
                if existing_w:
                    existing_w.delete()
                d.is_wicket = False
        d.save()
        state = recompute(innings)  # raises ScoringError if the edit makes the innings inconsistent
        # Free-hit flags of later balls may change after an edit.
        flags = {e["delivery_id"]: e["is_free_hit"] for e in state.events}
        for later in innings.deliveries.filter(voided=False, sequence__gt=d.sequence):
            if later.is_free_hit != flags.get(later.pk, later.is_free_hit):
                later.is_free_hit = flags[later.pk]
                later.save(update_fields=["is_free_hit"])
        is_last = not innings.deliveries.filter(voided=False, sequence__gt=d.sequence).exists()
        has_later_retirement = innings.dismissals.filter(voided=False, delivery__isnull=True,
                                                         after_sequence__gte=d.sequence).exists()
        if is_last and not has_later_retirement and innings.status == Innings.Status.IN_PROGRESS:
            d.refresh_from_db()
            _update_positions_after(innings, rules, d, state)
        reason_now = state.end_reason()
        is_latest = not match.innings.filter(number__gt=innings.number).exists()
        if innings.status == Innings.Status.IN_PROGRESS and reason_now:
            innings.save()
            _complete_innings(match, innings, reason_now, user)
        elif (innings.status == Innings.Status.COMPLETED and not reason_now and is_latest
              and innings.end_reason in ("all_out", "overs_complete", "target_reached")):
            innings.status = Innings.Status.IN_PROGRESS
            innings.end_reason = ""
            innings.ended_at = None
            if is_last:
                _update_positions_after(innings, rules, d, state)
            innings.save()
            _sync_result(match, user)
            match.status = Match.Status.LIVE
        else:
            innings.save()
            _sync_result(match, user)
            if any(i.status == Innings.Status.IN_PROGRESS for i in match.innings.all()):
                match.status = Match.Status.LIVE
        d.refresh_from_db()
        after = delivery_snapshot(d)
        ScoringCorrection.objects.create(match=match, innings=innings, delivery=d,
                                         action=ScoringCorrection.Action.EDIT, before=before, after=after,
                                         reason=reason, user=user)
        _bump(match, user, "edit", delivery=d.pk)
        return d


# ---------------------------------------------------------------------------
# Innings and match control
# ---------------------------------------------------------------------------
def end_innings(user, match_id, reason=Innings.EndReason.DECLARED):
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        _require_live(match)
        innings = _current_innings(match)
        if innings is None:
            raise ScoringError("No innings in progress.", "no_innings")
        if reason not in (Innings.EndReason.DECLARED, Innings.EndReason.INTERRUPTED):
            reason = Innings.EndReason.DECLARED
        recompute(innings)
        _complete_innings(match, innings, reason, user)
        _bump(match, user, "end_innings", innings=innings.number)
        return innings


def pause_match(user, match_id, reason=""):
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        if match.status not in (Match.Status.LIVE, Match.Status.INNINGS_BREAK, Match.Status.TOSS):
            raise ScoringError("Only a match in progress can be paused.", "invalid_state")
        match.status_before_pause = match.status
        match.status = Match.Status.PAUSED
        match.paused_at = timezone.now()
        match.pause_reason = (reason or "Interruption")[:200]
        _bump(match, user, "pause", reason=match.pause_reason)
        return match


def resume_match(user, match_id):
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        if match.status != Match.Status.PAUSED:
            raise ScoringError("The match is not paused.", "invalid_state")
        if match.paused_at:
            match.paused_seconds += int((timezone.now() - match.paused_at).total_seconds())
        match.status = match.status_before_pause or Match.Status.LIVE
        match.status_before_pause = ""
        match.paused_at = None
        match.pause_reason = ""
        _bump(match, user, "resume")
        return match


def revise_innings(user, match_id, max_overs=None, target=None, reason=""):
    """Reduce overs and/or set a revised target after an interruption.

    The revised target is entered by the officials (no DLS calculation is
    performed, as the DLS method requires licensed resource tables).
    """
    with transaction.atomic():
        match = _lock(match_id)
        _require_scorer(user, match)
        innings = _current_innings(match) or _latest_innings(match)
        if innings is None:
            raise ScoringError("No innings to revise.", "no_innings")
        state = replay(innings)
        if max_overs is not None:
            max_overs = int(max_overs)
            if max_overs < 1 or max_overs * match.rules["balls_per_over"] < state.legal_balls:
                raise ScoringError("Revised overs cannot be fewer than overs already bowled.", "invalid")
            innings.max_overs = max_overs
        if target is not None:
            if innings.number % 2 == 1:
                raise ScoringError("A target applies only to the chasing innings.", "invalid")
            innings.target = int(target)
        innings.save()
        state = recompute(innings)
        if innings.status == Innings.Status.IN_PROGRESS and state.end_reason():
            _complete_innings(match, innings, state.end_reason(), user)
        _bump(match, user, "revise", max_overs=innings.max_overs, target=innings.target, reason=reason)
        return innings
