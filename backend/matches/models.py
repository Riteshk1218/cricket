import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from tournaments.models import Ground, Player, Team, Tournament


class Match(models.Model):
    class Stage(models.TextChoices):
        LEAGUE = "league", "League"
        QUARTER_FINAL = "quarter_final", "Quarter-final"
        SEMI_FINAL = "semi_final", "Semi-final"
        FINAL = "final", "Final"
        KNOCKOUT = "knockout", "Knockout round"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        TOSS = "toss", "Toss done"
        LIVE = "live", "Live"
        INNINGS_BREAK = "innings_break", "Innings break"
        PAUSED = "paused", "Interrupted"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"

    class TossDecision(models.TextChoices):
        BAT = "bat", "Bat"
        BOWL = "bowl", "Bowl"

    LIVE_STATUSES = (Status.LIVE, Status.INNINGS_BREAK, Status.PAUSED)
    FINISHED_STATUSES = (Status.COMPLETED, Status.ABANDONED)

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="matches")
    match_number = models.PositiveSmallIntegerField(default=1)
    stage = models.CharField(max_length=16, choices=Stage.choices, default=Stage.LEAGUE)
    knockout_round = models.PositiveSmallIntegerField(null=True, blank=True)
    group = models.CharField(max_length=10, blank=True)
    team_a = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="home_matches")
    team_b = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="away_matches")
    ground = models.ForeignKey(Ground, null=True, blank=True, on_delete=models.SET_NULL, related_name="matches")
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    rules = models.JSONField(default=dict, blank=True)
    toss_winner = models.ForeignKey(Team, null=True, blank=True, on_delete=models.PROTECT, related_name="tosses_won")
    toss_decision = models.CharField(max_length=4, choices=TossDecision.choices, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    paused_seconds = models.PositiveIntegerField(default=0)
    pause_reason = models.CharField(max_length=200, blank=True)
    status_before_pause = models.CharField(max_length=16, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    # Incremented on every scoring change. Clients use it to discard stale updates.
    version = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at", "match_number"]
        verbose_name_plural = "matches"
        constraints = [
            models.CheckConstraint(name="match_distinct_teams", condition=~Q(team_a=F("team_b"))),
        ]
        indexes = [models.Index(fields=["tournament", "status"]), models.Index(fields=["status", "scheduled_at"])]

    def __str__(self):
        return f"{self.team_a.short_name} vs {self.team_b.short_name} (#{self.match_number})"

    @property
    def is_live(self):
        return self.status in self.LIVE_STATUSES

    def other_team(self, team):
        return self.team_b if team.pk == self.team_a_id else self.team_a


class MatchSquad(models.Model):
    """Playing XI (or playing side for local formats) for one team in one match."""

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="squad")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="+")
    player = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="match_squads")
    batting_order = models.PositiveSmallIntegerField(default=0)
    is_captain = models.BooleanField(default=False)
    is_wicket_keeper = models.BooleanField(default=False)

    class Meta:
        ordering = ["team", "batting_order"]
        constraints = [models.UniqueConstraint(fields=["match", "player"], name="uniq_match_player")]


class ScorerAssignment(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="scorer_assignments")
    scorer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scorer_assignments")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["match", "scorer"], name="uniq_match_scorer")]


class Innings(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    class EndReason(models.TextChoices):
        ALL_OUT = "all_out", "All out"
        OVERS = "overs_complete", "Overs complete"
        TARGET = "target_reached", "Target reached"
        DECLARED = "declared", "Declared / ended by scorer"
        INTERRUPTED = "interrupted", "Ended by interruption"

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="innings")
    number = models.PositiveSmallIntegerField()
    is_super_over = models.BooleanField(default=False)
    batting_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="+")
    bowling_team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.IN_PROGRESS)
    end_reason = models.CharField(max_length=16, choices=EndReason.choices, blank=True)
    max_overs = models.PositiveSmallIntegerField()
    max_wickets = models.PositiveSmallIntegerField()
    target = models.PositiveIntegerField(null=True, blank=True)
    # Live pointers to the current batters and bowler. Deliveries store their own copies.
    striker = models.ForeignKey(Player, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    non_striker = models.ForeignKey(Player, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    bowler = models.ForeignKey(Player, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    # Cached totals, recomputed from deliveries after every change.
    total_runs = models.PositiveIntegerField(default=0)
    wickets = models.PositiveSmallIntegerField(default=0)
    legal_balls = models.PositiveIntegerField(default=0)
    extras = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["match", "number"]
        verbose_name_plural = "innings"
        constraints = [
            models.UniqueConstraint(fields=["match", "number"], name="uniq_match_innings_number"),
            models.CheckConstraint(name="innings_distinct_teams", condition=~Q(batting_team=F("bowling_team"))),
        ]

    def __str__(self):
        return f"{self.match} — innings {self.number}"


class Delivery(models.Model):
    """One ball (legal or not) recorded by a scorer. This is the scoring event of record."""

    class ShotZone(models.TextChoices):
        FINE_LEG = "fine_leg", "Fine leg"
        SQUARE_LEG = "square_leg", "Square leg"
        MID_WICKET = "mid_wicket", "Mid-wicket"
        MID_ON = "mid_on", "Mid-on"
        STRAIGHT = "straight", "Straight"
        MID_OFF = "mid_off", "Mid-off"
        COVER = "cover", "Cover"
        POINT = "point", "Point"
        THIRD_MAN = "third_man", "Third man"

    innings = models.ForeignKey(Innings, on_delete=models.CASCADE, related_name="deliveries")
    sequence = models.PositiveIntegerField(help_text="Order of the delivery within the innings, starting at 1")
    client_event_id = models.UUIDField(default=uuid.uuid4, unique=True, help_text="Idempotency key sent by the scorer app")
    over_number = models.PositiveSmallIntegerField(help_text="0-based over index")
    ball_in_over = models.PositiveSmallIntegerField(help_text="Legal balls in this over including this one")
    striker = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="deliveries_faced")
    # Null only in "last man stands" formats when one batter bats alone.
    non_striker = models.ForeignKey(Player, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    bowler = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="deliveries_bowled")
    runs_bat = models.PositiveSmallIntegerField(default=0)
    wides = models.PositiveSmallIntegerField(default=0, help_text="Total wide runs including the wide penalty")
    noballs = models.PositiveSmallIntegerField(default=0, help_text="No-ball penalty runs")
    byes = models.PositiveSmallIntegerField(default=0)
    legbyes = models.PositiveSmallIntegerField(default=0)
    penalty_runs = models.PositiveSmallIntegerField(default=0, help_text="Penalty runs awarded to the batting side")
    is_boundary = models.BooleanField(default=False)
    is_free_hit = models.BooleanField(default=False)
    is_penalty_only = models.BooleanField(default=False, help_text="Penalty award that is not a ball")
    batters_crossed = models.BooleanField(null=True, blank=True, help_text="Override crossing on run-outs")
    is_wicket = models.BooleanField(default=False)
    shot_zone = models.CharField(max_length=12, choices=ShotZone.choices, blank=True)
    note = models.CharField(max_length=200, blank=True)
    voided = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["innings", "sequence"]
        verbose_name_plural = "deliveries"
        constraints = [
            models.UniqueConstraint(fields=["innings", "sequence"], condition=Q(voided=False), name="uniq_active_delivery_sequence"),
            models.CheckConstraint(name="delivery_not_wide_and_noball", condition=Q(wides=0) | Q(noballs=0)),
            models.CheckConstraint(name="delivery_no_bat_runs_on_wide", condition=Q(wides=0) | Q(runs_bat=0)),
            models.CheckConstraint(name="delivery_runs_reasonable", condition=Q(runs_bat__lte=10) & Q(byes__lte=10) & Q(legbyes__lte=10) & Q(wides__lte=15)),
        ]
        indexes = [
            models.Index(fields=["innings", "voided", "sequence"]),
            models.Index(fields=["bowler", "voided"]),
            models.Index(fields=["striker", "voided"]),
        ]

    @property
    def total_runs(self):
        return self.runs_bat + self.wides + self.noballs + self.byes + self.legbyes + self.penalty_runs

    @property
    def is_legal(self):
        return not self.is_penalty_only and self.wides == 0 and self.noballs == 0


class Wicket(models.Model):
    """A dismissal or retirement. Retirements between balls have no delivery."""

    class Kind(models.TextChoices):
        BOWLED = "bowled", "Bowled"
        CAUGHT = "caught", "Caught"
        CAUGHT_AND_BOWLED = "caught_and_bowled", "Caught and bowled"
        LBW = "lbw", "LBW"
        RUN_OUT = "run_out", "Run out"
        STUMPED = "stumped", "Stumped"
        HIT_WICKET = "hit_wicket", "Hit wicket"
        OBSTRUCTING = "obstructing_field", "Obstructing the field"
        HIT_TWICE = "hit_ball_twice", "Hit the ball twice"
        TIMED_OUT = "timed_out", "Timed out"
        RETIRED_OUT = "retired_out", "Retired out"
        RETIRED_HURT = "retired_hurt", "Retired hurt"

    BOWLER_CREDITED = {"bowled", "caught", "caught_and_bowled", "lbw", "stumped", "hit_wicket"}
    NOT_A_WICKET = {"retired_hurt"}
    NON_DELIVERY = {"timed_out", "retired_out", "retired_hurt"}

    innings = models.ForeignKey(Innings, on_delete=models.CASCADE, related_name="dismissals")
    delivery = models.OneToOneField(Delivery, null=True, blank=True, on_delete=models.CASCADE, related_name="wicket")
    after_sequence = models.PositiveIntegerField(default=0, help_text="For retirements: delivery sequence they follow")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    player_out = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="dismissals")
    bowler = models.ForeignKey(Player, null=True, blank=True, on_delete=models.PROTECT, related_name="wickets_taken")
    fielder = models.ForeignKey(Player, null=True, blank=True, on_delete=models.PROTECT, related_name="fielding_dismissals")
    positions_before = models.JSONField(default=dict, blank=True, help_text="Batter positions before a retirement, for undo")
    voided = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["innings", "after_sequence", "id"]


class ScoringCorrection(models.Model):
    """History of undo/edit operations with before and after snapshots."""

    class Action(models.TextChoices):
        UNDO = "undo", "Undo last action"
        EDIT = "edit", "Edit delivery"
        ADMIN_EDIT = "admin_edit", "Admin correction"
        REOPEN_INNINGS = "reopen_innings", "Reopen innings"

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="corrections")
    innings = models.ForeignKey(Innings, null=True, blank=True, on_delete=models.SET_NULL, related_name="corrections")
    delivery = models.ForeignKey(Delivery, null=True, blank=True, on_delete=models.SET_NULL, related_name="corrections")
    action = models.CharField(max_length=16, choices=Action.choices)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class MatchResult(models.Model):
    class Kind(models.TextChoices):
        RUNS = "runs", "Won by runs"
        WICKETS = "wickets", "Won by wickets"
        TIE = "tie", "Tie"
        SUPER_OVER = "super_over", "Won in super over"
        NO_RESULT = "no_result", "No result"
        ABANDONED = "abandoned", "Abandoned"
        AWARDED = "awarded", "Awarded / forfeit"

    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name="result")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    winner = models.ForeignKey(Team, null=True, blank=True, on_delete=models.PROTECT, related_name="wins")
    margin = models.PositiveIntegerField(null=True, blank=True)
    summary = models.CharField(max_length=200)
    player_of_match = models.ForeignKey(Player, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    submitted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.summary
