"""Player statistics computed directly from recorded deliveries.

Super-over deliveries are excluded, following common practice in official
records. Live matches are included so leaderboards update during play.
"""
from collections import defaultdict

from django.db.models import Count, F, Q, Sum

from matches.models import Delivery, Innings, Match, MatchSquad, Wicket

COUNTED_STATUSES = (Match.Status.LIVE, Match.Status.INNINGS_BREAK, Match.Status.PAUSED, Match.Status.COMPLETED,
                    Match.Status.ABANDONED)
BOWLER_CREDITED = ["bowled", "caught", "caught_and_bowled", "lbw", "stumped", "hit_wicket"]


def _innings_qs(tournament_id=None):
    qs = Innings.objects.filter(match__status__in=COUNTED_STATUSES, is_super_over=False)
    if tournament_id:
        qs = qs.filter(match__tournament_id=tournament_id)
    return qs


def _bpo_map(innings_ids):
    return {i.pk: i.match.rules.get("balls_per_over", 6)
            for i in Innings.objects.filter(pk__in=innings_ids).select_related("match")}


def _overs(balls, bpo=6):
    return f"{balls // bpo}.{balls % bpo}"


def compute_stats(tournament_id=None, player_ids=None):
    """Return {player_id: {batting, bowling, fielding, matches}}."""
    innings = _innings_qs(tournament_id)
    deliveries = Delivery.objects.filter(voided=False, innings__in=innings)
    wickets = Wicket.objects.filter(voided=False, innings__in=innings)
    if player_ids is not None:
        pids = list(player_ids)
        deliveries_bat = deliveries.filter(Q(striker_id__in=pids) | Q(non_striker_id__in=pids))
        deliveries_bowl = deliveries.filter(bowler_id__in=pids)
    else:
        deliveries_bat = deliveries_bowl = deliveries

    bat = defaultdict(lambda: {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": False})
    for row in deliveries_bat.filter(is_penalty_only=False).values("innings_id", "striker_id").annotate(
            runs=Sum("runs_bat"), balls=Count("id", filter=Q(wides=0)),
            fours=Count("id", filter=Q(is_boundary=True, runs_bat=4)),
            sixes=Count("id", filter=Q(is_boundary=True, runs_bat=6))):
        bat[(row["striker_id"], row["innings_id"])].update(
            runs=row["runs"] or 0, balls=row["balls"], fours=row["fours"], sixes=row["sixes"])
    for row in deliveries_bat.exclude(non_striker_id=None).values("innings_id", "non_striker_id").distinct():
        bat[(row["non_striker_id"], row["innings_id"])]
    outs = wickets.exclude(kind="retired_hurt")
    for row in outs.values("innings_id", "player_out_id"):
        bat[(row["player_out_id"], row["innings_id"])]["out"] = True

    bowl = defaultdict(lambda: {"balls": 0, "runs": 0, "wickets": 0, "maidens": 0, "wides": 0, "noballs": 0})
    for row in deliveries_bowl.filter(is_penalty_only=False).values("innings_id", "bowler_id").annotate(
            balls=Count("id", filter=Q(wides=0, noballs=0)),
            runs=Sum(F("runs_bat") + F("wides") + F("noballs")),
            wd=Count("id", filter=Q(wides__gt=0)), nb=Count("id", filter=Q(noballs__gt=0))):
        bowl[(row["bowler_id"], row["innings_id"])].update(
            balls=row["balls"], runs=row["runs"] or 0, wides=row["wd"], noballs=row["nb"])
    bpo = _bpo_map({k[1] for k in bowl})
    over_rows = deliveries_bowl.filter(is_penalty_only=False).values("innings_id", "over_number").annotate(
        bowlers=Count("bowler_id", distinct=True), legal=Count("id", filter=Q(wides=0, noballs=0)),
        runs=Sum(F("runs_bat") + F("wides") + F("noballs")))
    maiden_overs = {(r["innings_id"], r["over_number"]) for r in over_rows
                    if r["bowlers"] == 1 and r["runs"] == 0 and r["legal"] == bpo.get(r["innings_id"], 6)}
    if maiden_overs:
        for row in deliveries_bowl.values("innings_id", "over_number", "bowler_id").distinct():
            if (row["innings_id"], row["over_number"]) in maiden_overs:
                bowl[(row["bowler_id"], row["innings_id"])]["maidens"] += 1
    wq = wickets.filter(kind__in=BOWLER_CREDITED).exclude(bowler_id=None)
    if player_ids is not None:
        wq = wq.filter(bowler_id__in=player_ids)
    for row in wq.values("innings_id", "bowler_id").annotate(n=Count("id")):
        bowl[(row["bowler_id"], row["innings_id"])]["wickets"] = row["n"]

    fielding = defaultdict(lambda: {"catches": 0, "run_outs": 0, "stumpings": 0})
    fq = wickets.exclude(fielder_id=None)
    if player_ids is not None:
        fq = fq.filter(fielder_id__in=player_ids)
    for row in fq.values("fielder_id", "kind").annotate(n=Count("id")):
        key = {"caught": "catches", "caught_and_bowled": "catches", "run_out": "run_outs", "stumped": "stumpings"}.get(row["kind"])
        if key:
            fielding[row["fielder_id"]][key] += row["n"]

    squads = MatchSquad.objects.filter(match__status__in=COUNTED_STATUSES, match__innings__isnull=False)
    if tournament_id:
        squads = squads.filter(match__tournament_id=tournament_id)
    if player_ids is not None:
        squads = squads.filter(player_id__in=player_ids)
    matches = {r["player_id"]: r["n"] for r in squads.values("player_id").annotate(n=Count("match", distinct=True))}

    result = defaultdict(lambda: {"matches": 0})
    for pid, n in matches.items():
        result[pid]["matches"] = n
    per_player_bat = defaultdict(list)
    for (pid, inn), line in bat.items():
        per_player_bat[pid].append(line)
    for pid, lines in per_player_bat.items():
        runs = sum(x["runs"] for x in lines)
        balls = sum(x["balls"] for x in lines)
        outs_n = sum(1 for x in lines if x["out"])
        best = max(lines, key=lambda x: (x["runs"], not x["out"]))
        result[pid]["batting"] = {
            "innings": len(lines), "runs": runs, "balls": balls, "not_outs": len(lines) - outs_n,
            "average": round(runs / outs_n, 2) if outs_n else None,
            "strike_rate": round(runs * 100 / balls, 2) if balls else 0.0,
            "fours": sum(x["fours"] for x in lines), "sixes": sum(x["sixes"] for x in lines),
            "highest": f"{best['runs']}{'' if best['out'] else '*'}", "highest_runs": best["runs"],
            "fifties": sum(1 for x in lines if 50 <= x["runs"] < 100),
            "hundreds": sum(1 for x in lines if x["runs"] >= 100),
            "ducks": sum(1 for x in lines if x["runs"] == 0 and x["out"]),
        }
    per_player_bowl = defaultdict(list)
    for (pid, inn), line in bowl.items():
        per_player_bowl[pid].append((inn, line))
    for pid, lines in per_player_bowl.items():
        balls = sum(x["balls"] for _, x in lines)
        runs = sum(x["runs"] for _, x in lines)
        wkts = sum(x["wickets"] for _, x in lines)
        b = bpo.get(lines[0][0], 6)
        best = max(lines, key=lambda t: (t[1]["wickets"], -t[1]["runs"]))[1]
        result[pid]["bowling"] = {
            "innings": len(lines), "balls": balls, "overs": _overs(balls, b), "runs": runs, "wickets": wkts,
            "maidens": sum(x["maidens"] for _, x in lines),
            "economy": round(runs * b / balls, 2) if balls else None,
            "average": round(runs / wkts, 2) if wkts else None,
            "strike_rate": round(balls / wkts, 2) if wkts else None,
            "best": f"{best['wickets']}/{best['runs']}", "best_wickets": best["wickets"], "best_runs": best["runs"],
            "wides": sum(x["wides"] for _, x in lines), "noballs": sum(x["noballs"] for _, x in lines),
            "four_wickets": sum(1 for _, x in lines if x["wickets"] >= 4),
            "five_wickets": sum(1 for _, x in lines if x["wickets"] >= 5),
        }
    for pid, f in fielding.items():
        result[pid]["fielding"] = f
    empty_bat = {"innings": 0, "runs": 0, "balls": 0, "not_outs": 0, "average": None, "strike_rate": 0.0,
                 "fours": 0, "sixes": 0, "highest": "-", "highest_runs": 0, "fifties": 0, "hundreds": 0, "ducks": 0}
    empty_bowl = {"innings": 0, "balls": 0, "overs": "0.0", "runs": 0, "wickets": 0, "maidens": 0, "economy": None,
                  "average": None, "strike_rate": None, "best": "-", "best_wickets": 0, "best_runs": 0,
                  "wides": 0, "noballs": 0, "four_wickets": 0, "five_wickets": 0}
    for pid in list(result.keys()) + list(player_ids or []):
        r = result[pid]
        r.setdefault("batting", dict(empty_bat))
        r.setdefault("bowling", dict(empty_bowl))
        r.setdefault("fielding", {"catches": 0, "run_outs": 0, "stumpings": 0})
    return dict(result)


def player_stats(player_id, tournament_id=None):
    return compute_stats(tournament_id, [player_id]).get(player_id)


def leaderboards(tournament_id=None, limit=10, min_balls_sr=20, min_balls_econ=24):
    from tournaments.models import Player

    stats = compute_stats(tournament_id)
    players = {p.pk: p for p in Player.objects.filter(pk__in=stats.keys()).select_related("team")}

    def row(pid, value, extra=None):
        p = players.get(pid)
        d = {"player_id": pid, "name": p.full_name if p else str(pid), "team": p.team.short_name if p and p.team else "",
             "value": value}
        d.update(extra or {})
        return d

    def top(key_fn, filt, reverse=True, value_fn=None, extra_fn=None):
        items = [(pid, s) for pid, s in stats.items() if filt(s)]
        items.sort(key=lambda t: key_fn(t[1]), reverse=reverse)
        return [row(pid, (value_fn or key_fn)(s), extra_fn(s) if extra_fn else None) for pid, s in items[:limit]]

    return {
        "most_runs": top(lambda s: s["batting"]["runs"], lambda s: s["batting"]["runs"] > 0,
                         extra_fn=lambda s: {"innings": s["batting"]["innings"], "strike_rate": s["batting"]["strike_rate"]}),
        "most_wickets": top(lambda s: (s["bowling"]["wickets"], -(s["bowling"]["economy"] or 0)),
                            lambda s: s["bowling"]["wickets"] > 0, value_fn=lambda s: s["bowling"]["wickets"],
                            extra_fn=lambda s: {"overs": s["bowling"]["overs"], "economy": s["bowling"]["economy"]}),
        "highest_strike_rate": top(lambda s: s["batting"]["strike_rate"], lambda s: s["batting"]["balls"] >= min_balls_sr,
                                   extra_fn=lambda s: {"runs": s["batting"]["runs"], "balls": s["batting"]["balls"]}),
        "best_economy": top(lambda s: s["bowling"]["economy"] or 0, lambda s: s["bowling"]["balls"] >= min_balls_econ,
                            reverse=False, extra_fn=lambda s: {"overs": s["bowling"]["overs"], "wickets": s["bowling"]["wickets"]}),
        "most_sixes": top(lambda s: s["batting"]["sixes"], lambda s: s["batting"]["sixes"] > 0),
        "most_fours": top(lambda s: s["batting"]["fours"], lambda s: s["batting"]["fours"] > 0),
        "highest_scores": top(lambda s: s["batting"]["highest_runs"], lambda s: s["batting"]["innings"] > 0,
                              value_fn=lambda s: s["batting"]["highest"]),
        "most_catches": top(lambda s: s["fielding"]["catches"], lambda s: s["fielding"]["catches"] > 0),
        "criteria": {"min_balls_strike_rate": min_balls_sr, "min_balls_economy": min_balls_econ},
    }
