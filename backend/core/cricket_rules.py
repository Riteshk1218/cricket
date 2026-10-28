"""Configurable playing conditions.

Each tournament stores default playing conditions, and each match keeps its
own copy so rules can be adjusted per match (for example after a rain delay)
without affecting other matches. Defaults follow the MCC Laws of Cricket and
common limited-overs playing conditions; local formats (box cricket,
tennis-ball cricket) override the relevant values.
"""
from copy import deepcopy

FORMAT_T10 = "T10"
FORMAT_T20 = "T20"
FORMAT_ODI = "ODI"
FORMAT_CUSTOM = "CUSTOM"
FORMAT_CHOICES = [
    (FORMAT_T10, "T10 (10 overs)"),
    (FORMAT_T20, "T20 (20 overs)"),
    (FORMAT_ODI, "One Day (50 overs)"),
    (FORMAT_CUSTOM, "Custom overs"),
]

BALL_LEATHER = "leather"
BALL_TENNIS = "tennis"
BALL_BOX = "box"
BALL_TYPE_CHOICES = [
    (BALL_LEATHER, "Leather ball"),
    (BALL_TENNIS, "Tennis ball"),
    (BALL_BOX, "Box cricket"),
]

ALL_DISMISSALS = [
    "bowled", "caught", "caught_and_bowled", "lbw", "run_out", "stumped", "hit_wicket",
    "obstructing_field", "hit_ball_twice", "timed_out", "retired_out", "retired_hurt",
]

BASE_RULES = {
    "overs_per_innings": 20,
    "balls_per_over": 6,
    "players_per_side": 11,
    # None means "no limit"; otherwise the maximum overs one bowler may bowl.
    "max_overs_per_bowler": 4,
    "wide_runs": 1,
    "noball_runs": 1,
    "free_hit_on_noball": True,
    "free_hit_on_wide": False,
    # Powerplay ranges are 1-based inclusive over numbers, e.g. [[1, 6]].
    "powerplays": [[1, 6]],
    "super_over_on_tie": True,
    "super_over_overs": 1,
    "super_over_wickets": 2,
    # Law 18.11 (2022): after a catch, the new batter takes strike unless the over ended.
    "caught_new_batter_on_strike": True,
    # Box cricket: last remaining batter may continue alone.
    "last_man_stands": False,
    # Dismissals not permitted under local rules (e.g. ["lbw"] for tennis-ball games).
    "disallowed_dismissals": [],
    "consecutive_overs_allowed": False,
}

FORMAT_PRESETS = {
    FORMAT_T10: {"overs_per_innings": 10, "max_overs_per_bowler": 2, "powerplays": [[1, 3]]},
    FORMAT_T20: {"overs_per_innings": 20, "max_overs_per_bowler": 4, "powerplays": [[1, 6]]},
    FORMAT_ODI: {"overs_per_innings": 50, "max_overs_per_bowler": 10, "powerplays": [[1, 10], [11, 40], [41, 50]],
                 "free_hit_on_noball": True},
    FORMAT_CUSTOM: {},
}

BALL_TYPE_PRESETS = {
    BALL_LEATHER: {},
    BALL_TENNIS: {"disallowed_dismissals": ["lbw"]},
    BALL_BOX: {"players_per_side": 8, "last_man_stands": True, "disallowed_dismissals": ["lbw"],
               "free_hit_on_wide": False},
}


def default_rules(match_format=FORMAT_T20, ball_type=BALL_LEATHER, overs=None):
    rules = deepcopy(BASE_RULES)
    rules.update(deepcopy(FORMAT_PRESETS.get(match_format, {})))
    rules.update(deepcopy(BALL_TYPE_PRESETS.get(ball_type, {})))
    if overs:
        rules["overs_per_innings"] = int(overs)
        if match_format == FORMAT_CUSTOM:
            rules["max_overs_per_bowler"] = max(1, -(-int(overs) // 5))
            rules["powerplays"] = [[1, max(1, int(overs) * 3 // 10)]]
    return rules


def normalize_rules(rules):
    """Fill in missing keys and validate value ranges. Returns a new dict."""
    from django.core.exceptions import ValidationError

    merged = deepcopy(BASE_RULES)
    merged.update(rules or {})
    errors = {}
    for key in ("overs_per_innings", "balls_per_over", "players_per_side", "wide_runs", "noball_runs",
                "super_over_overs", "super_over_wickets"):
        try:
            merged[key] = int(merged[key])
        except (TypeError, ValueError):
            errors[key] = "Must be a whole number."
    if not errors:
        if not 1 <= merged["overs_per_innings"] <= 100:
            errors["overs_per_innings"] = "Must be between 1 and 100."
        if not 4 <= merged["balls_per_over"] <= 10:
            errors["balls_per_over"] = "Must be between 4 and 10."
        if not 2 <= merged["players_per_side"] <= 15:
            errors["players_per_side"] = "Must be between 2 and 15."
        if not 0 <= merged["wide_runs"] <= 5 or not 0 <= merged["noball_runs"] <= 5:
            errors["wide_runs"] = "Wide and no-ball runs must be between 0 and 5."
    mob = merged.get("max_overs_per_bowler")
    if mob in ("", None):
        merged["max_overs_per_bowler"] = None
    else:
        try:
            merged["max_overs_per_bowler"] = int(mob)
            if merged["max_overs_per_bowler"] < 1:
                raise ValueError
        except (TypeError, ValueError):
            errors["max_overs_per_bowler"] = "Must be a positive whole number or empty."
    bad = [d for d in merged.get("disallowed_dismissals") or [] if d not in ALL_DISMISSALS]
    if bad:
        errors["disallowed_dismissals"] = f"Unknown dismissal types: {', '.join(bad)}"
    pps = merged.get("powerplays") or []
    try:
        merged["powerplays"] = [[int(a), int(b)] for a, b in pps if int(a) <= int(b)]
    except (TypeError, ValueError):
        errors["powerplays"] = "Use a list of [start_over, end_over] pairs."
    for key in ("free_hit_on_noball", "free_hit_on_wide", "super_over_on_tie", "caught_new_batter_on_strike",
                "last_man_stands", "consecutive_overs_allowed"):
        merged[key] = bool(merged.get(key))
    if errors:
        raise ValidationError(errors)
    return merged


def max_wickets(rules, players_available=None):
    """Wickets needed to bowl a side out."""
    players = players_available or rules["players_per_side"]
    return players if rules.get("last_man_stands") else players - 1
