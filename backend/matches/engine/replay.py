"""Pure-Python innings replay.

The scoring engine never mutates running totals in place. Every delivery is
stored as an immutable structured event, and the innings state (score,
scorecards, fall of wickets, partnerships, overs) is rebuilt by replaying the
events in order. This makes undo and edits safe: change an event, replay, and
every derived number is consistent again.

Nothing in this module touches the database, so it is easy to unit test.
Deliveries and wickets are any objects exposing the attributes used below
(Django model instances or simple namespaces in tests).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from core.exceptions import ScoringError

BOWLER_CREDITED = {"bowled", "caught", "caught_and_bowled", "lbw", "stumped", "hit_wicket"}
NOT_A_WICKET = {"retired_hurt"}

# Dismissals that are possible on each kind of delivery (MCC Laws 21, 22, 41).
DISMISSALS_ON_NOBALL = {"run_out", "obstructing_field", "hit_ball_twice"}
DISMISSALS_ON_WIDE = {"run_out", "stumped", "hit_wicket", "obstructing_field"}
DISMISSALS_ON_FREE_HIT = {"run_out", "obstructing_field", "hit_ball_twice"}
DELIVERY_DISMISSALS = {
    "bowled", "caught", "caught_and_bowled", "lbw", "run_out", "stumped", "hit_wicket",
    "obstructing_field", "hit_ball_twice",
}
NON_STRIKER_DISMISSALS = {"run_out", "obstructing_field"}

DISMISSAL_TEXT = {
    "bowled": "b {bowler}",
    "caught": "c {fielder} b {bowler}",
    "caught_and_bowled": "c & b {bowler}",
    "lbw": "lbw b {bowler}",
    "run_out": "run out ({fielder})",
    "stumped": "st {fielder} b {bowler}",
    "hit_wicket": "hit wicket b {bowler}",
    "obstructing_field": "obstructing the field",
    "hit_ball_twice": "hit the ball twice",
    "timed_out": "timed out",
    "retired_out": "retired out",
    "retired_hurt": "retired hurt",
}


def overs_text(legal_balls, balls_per_over=6):
    return f"{legal_balls // balls_per_over}.{legal_balls % balls_per_over}"


def rate(runs, balls, balls_per_over=6):
    return round(runs * balls_per_over / balls, 2) if balls else 0.0


def ball_label(d):
    """Short label used in over summaries, e.g. '4', 'W', '2wd', 'nb1', '1lb'."""
    if d.is_penalty_only:
        return f"{d.penalty_runs}P"
    parts = []
    if d.wides:
        parts.append("wd" if d.wides == 1 else f"{d.wides}wd")
    elif d.noballs:
        extra = d.runs_bat + d.byes + d.legbyes
        parts.append(f"nb{extra}" if extra else "nb")
    elif d.byes:
        parts.append(f"{d.byes}b")
    elif d.legbyes:
        parts.append(f"{d.legbyes}lb")
    else:
        parts.append(str(d.runs_bat))
    if d.penalty_runs:
        parts.append(f"+{d.penalty_runs}P")
    label = "".join(parts)
    if d.is_wicket:
        label = "W" if label == "0" else f"{label}W"
    return label


@dataclass
class BatterLine:
    player_id: int
    name: str
    order: int
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    dots: int = 0
    is_out: bool = False
    retired_hurt: bool = False
    dismissal: str = ""
    dismissal_text: str = "not out"
    bowler_id: int | None = None
    fielder_id: int | None = None

    @property
    def strike_rate(self):
        return round(self.runs * 100 / self.balls, 2) if self.balls else 0.0

    def as_dict(self):
        d = asdict(self)
        d["strike_rate"] = self.strike_rate
        return d


@dataclass
class BowlerLine:
    player_id: int
    name: str
    order: int
    balls: int = 0
    runs: int = 0
    wickets: int = 0
    maidens: int = 0
    wides: int = 0
    noballs: int = 0
    dots: int = 0
    fours: int = 0
    sixes: int = 0
    balls_per_over: int = 6

    @property
    def overs(self):
        return overs_text(self.balls, self.balls_per_over)

    @property
    def economy(self):
        return rate(self.runs, self.balls, self.balls_per_over)

    def as_dict(self):
        d = asdict(self)
        d.pop("balls_per_over")
        d["overs"] = self.overs
        d["economy"] = self.economy
        return d


@dataclass
class OverSummary:
    number: int  # 1-based for display
    bowler_id: int
    bowler: str
    runs: int = 0
    wickets: int = 0
    balls: list = field(default_factory=list)
    legal_balls: int = 0
    score_at_end: str = ""
    complete: bool = False


@dataclass
class InningsState:
    balls_per_over: int
    max_overs: int
    max_wickets: int
    target: int | None
    total: int = 0
    wickets: int = 0
    legal_balls: int = 0
    wides: int = 0
    noballs: int = 0
    byes: int = 0
    legbyes: int = 0
    penalty: int = 0
    batters: dict = field(default_factory=dict)
    bowlers: dict = field(default_factory=dict)
    overs: list = field(default_factory=list)
    fall_of_wickets: list = field(default_factory=list)
    partnerships: list = field(default_factory=list)
    free_hit_next: bool = False
    last_sequence: int = 0
    # Over number (0-based) and ball_in_over for each delivery id, recomputed on every replay.
    numbering: dict = field(default_factory=dict)
    # Bowler of the most recently *completed* over, for the consecutive-overs rule.
    last_completed_over_bowler: int | None = None
    current_over_bowler: int | None = None
    current_over_bowlers: set = field(default_factory=set)
    events: list = field(default_factory=list)

    @property
    def extras(self):
        return self.wides + self.noballs + self.byes + self.legbyes + self.penalty

    @property
    def max_balls(self):
        return self.max_overs * self.balls_per_over

    @property
    def balls_remaining(self):
        return max(0, self.max_balls - self.legal_balls)

    @property
    def balls_in_current_over(self):
        return self.legal_balls % self.balls_per_over

    @property
    def run_rate(self):
        return rate(self.total, self.legal_balls, self.balls_per_over)

    @property
    def runs_needed(self):
        return None if self.target is None else max(0, self.target - self.total)

    @property
    def required_run_rate(self):
        if self.target is None:
            return None
        if self.balls_remaining == 0:
            return None
        return rate(self.runs_needed, self.balls_remaining, self.balls_per_over)

    @property
    def is_all_out(self):
        return self.wickets >= self.max_wickets

    @property
    def overs_complete(self):
        return self.legal_balls >= self.max_balls

    @property
    def target_reached(self):
        return self.target is not None and self.total >= self.target

    def end_reason(self):
        if self.target_reached:
            return "target_reached"
        if self.is_all_out:
            return "all_out"
        if self.overs_complete:
            return "overs_complete"
        return None

    def batter_is_available(self, player_id):
        line = self.batters.get(player_id)
        return line is None or (not line.is_out)

    def overs_by_bowler(self, player_id):
        line = self.bowlers.get(player_id)
        return 0 if line is None else line.balls / self.balls_per_over

    def summary(self):
        return {
            "total": self.total,
            "wickets": self.wickets,
            "legal_balls": self.legal_balls,
            "overs": overs_text(self.legal_balls, self.balls_per_over),
            "max_overs": self.max_overs,
            "run_rate": self.run_rate,
            "target": self.target,
            "runs_needed": self.runs_needed,
            "balls_remaining": self.balls_remaining,
            "required_run_rate": self.required_run_rate,
            "extras": {
                "total": self.extras, "wides": self.wides, "noballs": self.noballs,
                "byes": self.byes, "legbyes": self.legbyes, "penalty": self.penalty,
            },
            "free_hit_next": self.free_hit_next,
        }

    def as_dict(self):
        data = self.summary()
        data["batting"] = [b.as_dict() for b in sorted(self.batters.values(), key=lambda b: b.order)]
        data["bowling"] = [b.as_dict() for b in sorted(self.bowlers.values(), key=lambda b: b.order)]
        data["fall_of_wickets"] = self.fall_of_wickets
        data["partnerships"] = self.partnerships
        data["overs_detail"] = [asdict(o) for o in self.overs]
        return data


def _name(names, pid):
    return names.get(pid, f"Player {pid}") if pid else ""


class _Replayer:
    def __init__(self, rules, max_overs, max_wickets, target, names):
        self.rules = rules
        self.names = names
        self.bpo = rules["balls_per_over"]
        self.state = InningsState(self.bpo, max_overs, max_wickets, target)
        self.over_runs_by_bowler = {}
        self.partnership = None

    # -- helpers -----------------------------------------------------------
    def batter(self, pid):
        st = self.state
        if pid not in st.batters:
            st.batters[pid] = BatterLine(pid, _name(self.names, pid), len(st.batters) + 1)
        return st.batters[pid]

    def bowler(self, pid):
        st = self.state
        if pid not in st.bowlers:
            st.bowlers[pid] = BowlerLine(pid, _name(self.names, pid), len(st.bowlers) + 1, balls_per_over=self.bpo)
        return st.bowlers[pid]

    def ensure_partnership(self, a, b):
        pair = {p for p in (a, b) if p}
        if self.partnership is None or set(self.partnership["batter_ids"]) != pair:
            if self.partnership is not None and self.partnership not in self.state.partnerships:
                self.state.partnerships.append(self.partnership)
            self.partnership = {
                "wicket": self.state.wickets + 1,
                "batter_ids": sorted(pair, key=lambda p: p != a),
                "batters": [_name(self.names, p) for p in sorted(pair, key=lambda p: p != a)],
                "runs": 0,
                "balls": 0,
                "contributions": {str(p): 0 for p in pair},
                "unbeaten": True,
            }

    def close_partnership(self):
        if self.partnership is not None:
            self.partnership["unbeaten"] = False
            self.state.partnerships.append(self.partnership)
            self.partnership = None

    def dismiss(self, wicket, delivery_bowler_id=None):
        st = self.state
        line = self.batter(wicket.player_out_id)
        if line.is_out:
            raise ScoringError(f"{line.name} is already out.", "already_out")
        kind = wicket.kind
        if kind in NOT_A_WICKET:
            line.retired_hurt = True
            line.dismissal = kind
            line.dismissal_text = "retired hurt"
            if self.partnership:
                self.close_partnership()
            return
        line.retired_hurt = False
        line.is_out = True
        line.dismissal = kind
        bowler_id = wicket.bowler_id if wicket.bowler_id else (delivery_bowler_id if kind in BOWLER_CREDITED else None)
        line.bowler_id = bowler_id if kind in BOWLER_CREDITED else None
        line.fielder_id = wicket.fielder_id
        line.dismissal_text = DISMISSAL_TEXT[kind].format(
            bowler=_name(self.names, bowler_id), fielder=_name(self.names, wicket.fielder_id) or "sub"
        ).replace("run out ()", "run out")
        st.wickets += 1
        st.fall_of_wickets.append({
            "wicket": st.wickets,
            "score": st.total,
            "overs": overs_text(st.legal_balls, self.bpo),
            "player_id": wicket.player_out_id,
            "player": line.name,
        })
        if kind in BOWLER_CREDITED and bowler_id:
            self.bowler(bowler_id).wickets += 1
        self.close_partnership()

    # -- main loop ---------------------------------------------------------
    def apply_delivery(self, d, wicket):
        st = self.state
        if st.end_reason() is not None:
            raise ScoringError("A delivery was recorded after the innings had ended.", "innings_over")
        for pid in (d.striker_id, d.non_striker_id):
            if pid is None:
                continue
            line = self.batter(pid)
            if line.is_out:
                raise ScoringError(f"{line.name} appears in a delivery after being dismissed.", "batter_out")
            if line.retired_hurt:
                line.retired_hurt = False
                line.dismissal = ""
                line.dismissal_text = "not out"
        if d.striker_id == d.non_striker_id:
            raise ScoringError("Striker and non-striker must be different players.", "same_batter")

        over_index = st.legal_balls // self.bpo
        is_legal = not d.is_penalty_only and d.wides == 0 and d.noballs == 0

        bowler = self.bowler(d.bowler_id)
        if not st.overs or st.overs[-1].complete:
            st.overs.append(OverSummary(number=over_index + 1, bowler_id=d.bowler_id, bowler=bowler.name))
            st.current_over_bowlers = set()
            self.over_runs_by_bowler = {}
        over = st.overs[-1]
        if over.bowler_id != d.bowler_id and d.bowler_id not in st.current_over_bowlers:
            # Mid-over bowler change (injury or suspension).
            over.bowler = f"{over.bowler} / {bowler.name}"
        st.current_over_bowler = d.bowler_id
        st.current_over_bowlers.add(d.bowler_id)

        total = d.runs_bat + d.wides + d.noballs + d.byes + d.legbyes + d.penalty_runs
        st.total += total
        st.wides += d.wides
        st.noballs += d.noballs
        st.byes += d.byes
        st.legbyes += d.legbyes
        st.penalty += d.penalty_runs

        if not d.is_penalty_only:
            striker = self.batter(d.striker_id)
            if d.wides == 0:
                striker.balls += 1
                striker.runs += d.runs_bat
                if d.runs_bat == 0:
                    striker.dots += 1
                if d.is_boundary and d.runs_bat == 4:
                    striker.fours += 1
                if d.is_boundary and d.runs_bat == 6:
                    striker.sixes += 1
            bowler_runs = d.runs_bat + d.wides + d.noballs
            bowler.runs += bowler_runs
            self.over_runs_by_bowler[d.bowler_id] = self.over_runs_by_bowler.get(d.bowler_id, 0) + bowler_runs
            if d.wides:
                bowler.wides += 1
            if d.noballs:
                bowler.noballs += 1
            if is_legal:
                bowler.balls += 1
                st.legal_balls += 1
                over.legal_balls += 1
                if total == 0:
                    bowler.dots += 1
            if d.is_boundary and d.runs_bat == 4:
                bowler.fours += 1
            if d.is_boundary and d.runs_bat == 6:
                bowler.sixes += 1
            self.ensure_partnership(d.striker_id, d.non_striker_id)
            self.partnership["runs"] += total
            self.partnership["contributions"][str(d.striker_id)] += d.runs_bat
            if d.wides == 0:
                self.partnership["balls"] += 1
        else:
            if self.partnership is not None:
                self.partnership["runs"] += total

        st.numbering[d.pk] = (over_index, over.legal_balls)
        over.runs += total
        over.balls.append(ball_label(d))

        is_free_hit = st.free_hit_next
        if wicket is not None:
            self.dismiss(wicket, d.bowler_id)
            over.wickets += 1

        # Free hit: follows a no-ball; carries over if the free-hit ball is itself a wide or no-ball.
        if d.noballs and self.rules.get("free_hit_on_noball", True):
            st.free_hit_next = True
        elif d.wides and (self.rules.get("free_hit_on_wide") or is_free_hit):
            st.free_hit_next = True
        elif is_legal:
            st.free_hit_next = False

        if is_legal and st.legal_balls % self.bpo == 0:
            over.complete = True
            over.score_at_end = f"{st.total}/{st.wickets}"
            if len(st.current_over_bowlers) == 1 and over.legal_balls == self.bpo and self.over_runs_by_bowler.get(d.bowler_id, 0) == 0:
                bowler.maidens += 1
            st.last_completed_over_bowler = d.bowler_id
            st.current_over_bowler = None
        st.last_sequence = d.sequence
        st.events.append({"delivery_id": d.pk, "is_free_hit": is_free_hit})

    def finish(self):
        if self.partnership is not None:
            self.state.partnerships.append(self.partnership)
            self.partnership = None
        return self.state


def replay_innings(rules, max_overs, max_wickets, target, deliveries, wickets_by_delivery, retirements, names,
                   initial_batters=()):
    """Rebuild an innings from its events.

    ``deliveries``: active deliveries ordered by sequence.
    ``wickets_by_delivery``: {delivery_pk: wicket} for dismissals on a ball.
    ``retirements``: non-delivery dismissals ordered by after_sequence.
    ``initial_batters``: openers, so they appear on the card before facing a ball.
    """
    r = _Replayer(rules, max_overs, max_wickets, target, names)
    for pid in initial_batters:
        if pid:
            r.batter(pid)
    pending = list(retirements)

    def flush_retirements(upto):
        while pending and pending[0].after_sequence <= upto:
            r.dismiss(pending.pop(0))

    flush_retirements(0)
    for d in deliveries:
        r.apply_delivery(d, wickets_by_delivery.get(d.pk))
        flush_retirements(d.sequence)
    flush_retirements(10**9)
    return r.finish()


def next_positions(rules, delivery, wicket_kind, player_out_id, striker_id, non_striker_id, over_complete):
    """Where the batters stand after a delivery. ``None`` marks a vacant end."""
    wide_penalty = rules.get("wide_runs", 1)
    if delivery.is_penalty_only:
        return striker_id, non_striker_id
    if delivery.is_boundary:
        runs_run = 0
    else:
        runs_run = delivery.runs_bat + delivery.byes + delivery.legbyes + max(0, delivery.wides - wide_penalty)
    crossings = runs_run + (1 if delivery.batters_crossed else 0)
    s, ns = striker_id, non_striker_id
    if non_striker_id is None:
        # Last man stands: the lone batter keeps strike.
        return (None if wicket_kind and player_out_id == striker_id else striker_id), None
    if crossings % 2 == 1:
        s, ns = ns, s
    if wicket_kind:
        if s == player_out_id:
            s = None
        elif ns == player_out_id:
            ns = None
        if wicket_kind in ("caught", "caught_and_bowled") and rules.get("caught_new_batter_on_strike", True):
            if s is not None and ns is None:
                s, ns = None, s
    if over_complete:
        s, ns = ns, s
    return s, ns


def validate_dismissal(rules, kind, delivery_kind, is_free_hit, out_is_striker):
    """Raise ScoringError if this dismissal is impossible on this delivery."""
    if kind in rules.get("disallowed_dismissals", []):
        raise ScoringError(f"'{kind}' is not allowed under this match's playing rules.", "dismissal_disallowed")
    if kind not in DELIVERY_DISMISSALS:
        raise ScoringError(f"'{kind}' is not a dismissal that happens on a delivery.", "invalid_dismissal")
    if delivery_kind == "wide" and kind not in DISMISSALS_ON_WIDE:
        raise ScoringError(f"A batter cannot be out '{kind}' off a wide.", "invalid_dismissal")
    if delivery_kind == "noball" and kind not in DISMISSALS_ON_NOBALL:
        raise ScoringError(f"A batter cannot be out '{kind}' off a no-ball.", "invalid_dismissal")
    if is_free_hit and delivery_kind not in ("wide", "noball") and kind not in DISMISSALS_ON_FREE_HIT:
        raise ScoringError(f"A batter cannot be out '{kind}' on a free hit.", "free_hit")
    if not out_is_striker and kind not in NON_STRIKER_DISMISSALS:
        raise ScoringError("The non-striker can only be run out or out obstructing the field.", "invalid_dismissal")
