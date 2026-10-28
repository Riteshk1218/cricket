"""Build the full live view of a match (scorecards, current state, commentary)."""
from django.core.cache import cache

from ..models import Innings, Match, MatchSquad
from .commentary import LANGUAGES, delivery_commentary, over_end_commentary, retirement_commentary
from .replay import ball_label, overs_text
from .service import player_names, replay

RECENT_COMMENTARY = 40


def _media(field):
    try:
        return field.url if field else None
    except ValueError:
        return None


def team_info(team):
    return {
        "id": team.id, "name": team.name, "short_name": team.short_name, "logo": _media(team.logo),
        "primary_color": team.primary_color,
    }


def highlight_for(d):
    if d.is_wicket:
        return "wicket"
    if d.is_boundary and d.runs_bat == 6:
        return "six"
    if d.is_boundary and d.runs_bat == 4:
        return "four"
    return None


def commentary_entries(innings, names, state, deliveries, limit=None, wickets=None):
    """Commentary for an innings, newest first, in all supported languages."""
    rules = innings.match.rules
    bpo = rules["balls_per_over"]
    wickets = wickets if wickets is not None else {
        w.delivery_id: w for w in innings.dismissals.filter(voided=False, delivery__isnull=False)}
    retirements = list(innings.dismissals.filter(voided=False, delivery__isnull=True))
    flags = {e["delivery_id"]: e["is_free_hit"] for e in state.events}
    entries = []
    over_runs = {}
    running = 0
    running_wkts = 0
    for i, d in enumerate(deliveries):
        w = wickets.get(d.pk)
        running += d.total_runs
        if w and w.kind != "retired_hurt":
            running_wkts += 1
        over_runs[d.over_number] = over_runs.get(d.over_number, 0) + d.total_runs
        nxt = deliveries[i + 1] if i + 1 < len(deliveries) else None
        next_free_hit = flags.get(nxt.pk) if nxt else state.free_hit_next
        text = {
            lang: delivery_commentary(
                lang, seed=d.sequence, batter=names.get(d.striker_id, ""), bowler=names.get(d.bowler_id, ""),
                runs_bat=d.runs_bat, wides=d.wides, noballs=d.noballs, byes=d.byes, legbyes=d.legbyes,
                penalty_runs=d.penalty_runs, is_boundary=d.is_boundary, is_penalty_only=d.is_penalty_only,
                shot_zone=d.shot_zone, wicket_kind=w.kind if w else None,
                player_out=names.get(w.player_out_id, "") if w else None,
                fielder=names.get(w.fielder_id) if w and w.fielder_id else None,
                next_is_free_hit=bool(d.noballs and next_free_hit), wide_runs=rules.get("wide_runs", 1),
            ) for lang in LANGUAGES
        }
        entries.append({
            "type": "ball", "delivery_id": d.pk, "sequence": d.sequence,
            "over": f"{d.over_number}.{d.ball_in_over}", "label": ball_label(d),
            "runs": d.total_runs, "highlight": highlight_for(d), "is_free_hit": d.is_free_hit,
            "batter": names.get(d.striker_id, ""), "bowler": names.get(d.bowler_id, ""),
            "score": f"{running}/{running_wkts}", "text": text, "note": d.note,
        })
        if d.is_legal and d.ball_in_over == bpo:
            score = f"{running}/{running_wkts}"
            entries.append({
                "type": "over_end", "over": d.over_number + 1, "sequence": d.sequence,
                "text": {lang: over_end_commentary(lang, d.over_number + 1, over_runs[d.over_number], score)
                         for lang in LANGUAGES},
            })
        for r in retirements:
            if r.after_sequence == d.sequence:
                entries.append({"type": "retirement", "sequence": d.sequence, "text": {
                    lang: retirement_commentary(lang, r.kind, names.get(r.player_out_id, "")) for lang in LANGUAGES}})
    entries.reverse()
    return entries[:limit] if limit else entries


def innings_payload(innings, names, with_commentary=False):
    deliveries = list(innings.deliveries.filter(voided=False).order_by("sequence"))
    state = replay(innings, names, deliveries)
    data = {
        "id": innings.id, "number": innings.number, "is_super_over": innings.is_super_over,
        "batting_team": team_info(innings.batting_team), "bowling_team": team_info(innings.bowling_team),
        "status": innings.status, "end_reason": innings.end_reason,
        "max_wickets": innings.max_wickets, "last_sequence": state.last_sequence,
    }
    data.update(state.as_dict())
    # Batters yet to bat.
    squad = MatchSquad.objects.filter(match=innings.match, team=innings.batting_team).order_by("batting_order")
    batted = {b["player_id"] for b in data["batting"]}
    data["yet_to_bat"] = [{"player_id": m.player_id, "name": names.get(m.player_id, "")}
                          for m in squad if m.player_id not in batted]
    return data, state, deliveries


def _powerplay(rules, legal_balls):
    over = legal_balls // rules["balls_per_over"] + 1
    for idx, (start, end) in enumerate(rules.get("powerplays") or []):
        if start <= over <= end:
            return {"active": True, "number": idx + 1, "overs": f"{start}-{end}"}
    return {"active": False}


def build_snapshot(match):
    key = f"match-snapshot:{match.pk}:{match.version}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    names = player_names(match)
    try:
        result = match.result
    except Match.result.RelatedObjectDoesNotExist:
        result = None
    innings_list = list(match.innings.select_related("batting_team", "bowling_team").order_by("number"))
    innings_data = []
    current = None
    commentary = []
    for inn in innings_list:
        data, state, deliveries = innings_payload(inn, names)
        innings_data.append(data)
        commentary = commentary_entries(inn, names, state, deliveries, limit=RECENT_COMMENTARY) + commentary
        if inn.status == Innings.Status.IN_PROGRESS or inn is innings_list[-1]:
            current = (inn, state, deliveries, data)
    snapshot = {
        "id": match.pk,
        "version": match.version,
        "status": match.status,
        "stage": match.stage,
        "match_number": match.match_number,
        "tournament": {"id": match.tournament_id, "name": match.tournament.name,
                       "logo": _media(match.tournament.logo), "match_format": match.tournament.match_format},
        "ground": str(match.ground) if match.ground else None,
        "scheduled_at": match.scheduled_at.isoformat(),
        "team_a": team_info(match.team_a),
        "team_b": team_info(match.team_b),
        "toss": None,
        "rules": match.rules,
        "clock": {
            "started_at": match.started_at.isoformat() if match.started_at else None,
            "paused_at": match.paused_at.isoformat() if match.paused_at else None,
            "paused_seconds": match.paused_seconds,
            "pause_reason": match.pause_reason,
            "completed_at": match.completed_at.isoformat() if match.completed_at else None,
        },
        "innings": innings_data,
        "current": None,
        "result": None,
        "commentary": commentary[:RECENT_COMMENTARY],
        "squads": {},
    }
    if match.toss_winner_id:
        winner = match.team_a if match.toss_winner_id == match.team_a_id else match.team_b
        snapshot["toss"] = {"winner": winner.id, "winner_name": winner.name, "decision": match.toss_decision,
                            "text": f"{winner.name} won the toss and chose to {match.toss_decision}"}
    for team in (match.team_a, match.team_b):
        snapshot["squads"][str(team.id)] = [
            {"player_id": m.player_id, "name": names.get(m.player_id, ""), "is_captain": m.is_captain,
             "is_wicket_keeper": m.is_wicket_keeper, "batting_order": m.batting_order}
            for m in MatchSquad.objects.filter(match=match, team=team).order_by("batting_order")
        ]
    if result is not None:
        snapshot["result"] = {
            "kind": result.kind, "winner": result.winner_id, "margin": result.margin, "summary": result.summary,
            "player_of_match": result.player_of_match_id,
            "player_of_match_name": names.get(result.player_of_match_id) if result.player_of_match_id else None,
        }
    if current is not None:
        inn, state, deliveries, data = current
        bat = {b["player_id"]: b for b in data["batting"]}
        bowl = {b["player_id"]: b for b in data["bowling"]}
        this_over = data["overs_detail"][-1] if data["overs_detail"] else None
        if this_over and this_over["complete"] and inn.status == Innings.Status.IN_PROGRESS:
            this_over = None
        partnership = data["partnerships"][-1] if data["partnerships"] and data["partnerships"][-1]["unbeaten"] else None
        snapshot["current"] = {
            "innings_id": inn.id,
            "innings_number": inn.number,
            "is_super_over": inn.is_super_over,
            "in_progress": inn.status == Innings.Status.IN_PROGRESS,
            "batting_team": data["batting_team"],
            "bowling_team": data["bowling_team"],
            "score": f"{state.total}/{state.wickets}",
            "overs": overs_text(state.legal_balls, state.balls_per_over),
            "striker": bat.get(inn.striker_id) or ({"player_id": inn.striker_id, "name": names.get(inn.striker_id), "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "strike_rate": 0} if inn.striker_id else None),
            "non_striker": bat.get(inn.non_striker_id) or ({"player_id": inn.non_striker_id, "name": names.get(inn.non_striker_id), "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "strike_rate": 0} if inn.non_striker_id else None),
            "bowler": bowl.get(inn.bowler_id) or ({"player_id": inn.bowler_id, "name": names.get(inn.bowler_id), "overs": "0.0", "runs": 0, "wickets": 0, "maidens": 0, "economy": 0} if inn.bowler_id else None),
            "last_over_bowler": state.last_completed_over_bowler,
            "partnership": partnership,
            "this_over": this_over,
            "recent_balls": [ball_label(d) for d in deliveries[-12:]],
            "run_rate": state.run_rate,
            "required_run_rate": state.required_run_rate,
            "target": state.target,
            "runs_needed": state.runs_needed,
            "balls_remaining": state.balls_remaining,
            "free_hit": state.free_hit_next,
            "powerplay": _powerplay(match.rules, state.legal_balls),
            "last_sequence": state.last_sequence,
            "balls_in_over": state.balls_in_current_over,
            "need_batter": inn.status == Innings.Status.IN_PROGRESS and (not inn.striker_id or (not inn.non_striker_id and not match.rules.get("last_man_stands"))),
            "need_bowler": inn.status == Innings.Status.IN_PROGRESS and not inn.bowler_id,
        }
        if state.target is not None and inn.status == Innings.Status.IN_PROGRESS:
            snapshot["current"]["equation"] = (
                f"{data['batting_team']['name']} need {state.runs_needed} run{'s' if state.runs_needed != 1 else ''} "
                f"from {state.balls_remaining} ball{'s' if state.balls_remaining != 1 else ''}")
    cache.set(key, snapshot, 300)
    return snapshot


def match_summary(match):
    """Compact card data for match lists and the live ticker."""
    innings = list(match.innings.select_related("batting_team").order_by("number"))
    scores = {}
    for inn in innings:
        entry = scores.setdefault(str(inn.batting_team_id), [])
        entry.append({
            "innings": inn.number, "runs": inn.total_runs, "wickets": inn.wickets,
            "overs": overs_text(inn.legal_balls, match.rules.get("balls_per_over", 6)),
            "is_super_over": inn.is_super_over,
        })
    try:
        result = match.result.summary
    except Match.result.RelatedObjectDoesNotExist:
        result = None
    current = next((i for i in reversed(innings) if i.status == Innings.Status.IN_PROGRESS), None)
    return {
        "id": match.pk, "version": match.version, "status": match.status, "stage": match.stage,
        "match_number": match.match_number, "scheduled_at": match.scheduled_at.isoformat(),
        "tournament": {"id": match.tournament_id, "name": match.tournament.name},
        "ground": str(match.ground) if match.ground else None,
        "team_a": team_info(match.team_a), "team_b": team_info(match.team_b),
        "scores": scores, "result": result,
        "batting_team_id": current.batting_team_id if current else None,
        "target": current.target if current else None,
    }
