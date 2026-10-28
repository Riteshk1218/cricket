from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.text import slugify

from core.cricket_rules import BALL_LEATHER, BALL_TYPE_CHOICES, FORMAT_CHOICES, FORMAT_T20, default_rules, normalize_rules


class Ground(models.Model):
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["name", "city"], name="uniq_ground_name_city")]

    def __str__(self):
        return f"{self.name}, {self.city}" if self.city else self.name


class Tournament(models.Model):
    class Kind(models.TextChoices):
        LEAGUE = "league", "League (round robin + playoffs)"
        KNOCKOUT = "knockout", "Knockout"

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    short_name = models.CharField(max_length=20, blank=True)
    logo = models.ImageField(upload_to="tournaments/", blank=True, null=True)
    location = models.CharField(max_length=150, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.LEAGUE)
    match_format = models.CharField(max_length=8, choices=FORMAT_CHOICES, default=FORMAT_T20)
    ball_type = models.CharField(max_length=12, choices=BALL_TYPE_CHOICES, default=BALL_LEATHER)
    rules = models.JSONField(default=dict, blank=True, help_text="Default playing conditions for matches")
    points_win = models.PositiveSmallIntegerField(default=2)
    points_tie = models.PositiveSmallIntegerField(default=1)
    points_no_result = models.PositiveSmallIntegerField(default=1)
    points_loss = models.PositiveSmallIntegerField(default=0)
    playoff_teams = models.PositiveSmallIntegerField(default=4, help_text="2 = final only, 4 = semifinals + final")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPCOMING, db_index=True)
    winner = models.ForeignKey("Team", null=True, blank=True, on_delete=models.SET_NULL, related_name="tournaments_won")
    runner_up = models.ForeignKey("Team", null=True, blank=True, on_delete=models.SET_NULL, related_name="tournaments_runner_up")
    grounds = models.ManyToManyField(Ground, blank=True, related_name="tournaments")
    admins = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="managed_tournaments")
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "name"]
        constraints = [
            models.CheckConstraint(name="tournament_dates_ordered", condition=Q(end_date__gte=F("start_date"))),
            models.CheckConstraint(name="tournament_playoff_teams", condition=Q(playoff_teams__in=[0, 2, 4])),
        ]

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date must be on or after the start date."})

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:150] or "tournament"
            slug, n = base, 2
            while Tournament.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        if not self.rules:
            self.rules = default_rules(self.match_format, self.ball_type)
        self.rules = normalize_rules(self.rules)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=120, unique=True)
    short_name = models.CharField(max_length=6)
    logo = models.ImageField(upload_to="teams/", blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#0f766e")
    city = models.CharField(max_length=80, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Player(models.Model):
    class Role(models.TextChoices):
        BATTER = "batter", "Batter"
        BOWLER = "bowler", "Bowler"
        ALL_ROUNDER = "all_rounder", "All-rounder"
        WICKET_KEEPER = "wicket_keeper", "Wicket-keeper"

    class BattingStyle(models.TextChoices):
        RIGHT = "right", "Right-hand bat"
        LEFT = "left", "Left-hand bat"

    full_name = models.CharField(max_length=120)
    short_name = models.CharField(max_length=40, blank=True, help_text="Name shown on scorecards")
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="players")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.BATTER)
    batting_style = models.CharField(max_length=8, choices=BattingStyle.choices, default=BattingStyle.RIGHT)
    bowling_style = models.CharField(max_length=60, blank=True)
    jersey_number = models.PositiveSmallIntegerField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to="players/", blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]
        indexes = [models.Index(fields=["team", "full_name"])]

    def save(self, *args, **kwargs):
        if not self.short_name:
            parts = self.full_name.split()
            self.short_name = f"{parts[0][0]} {' '.join(parts[1:])}" if len(parts) > 1 else self.full_name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name


class TournamentRegistration(models.Model):
    """A team entered in a tournament, with its registered squad."""

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="registrations")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="registrations")
    group = models.CharField(max_length=10, blank=True, default="A")
    players = models.ManyToManyField(Player, blank=True, related_name="tournament_registrations")
    seed = models.PositiveSmallIntegerField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["group", "seed", "team__name"]
        constraints = [models.UniqueConstraint(fields=["tournament", "team"], name="uniq_tournament_team")]

    def __str__(self):
        return f"{self.team} @ {self.tournament}"


class PointsTableEntry(models.Model):
    """Materialised points table row, recalculated whenever a league result changes."""

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="points_table")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="points_entries")
    group = models.CharField(max_length=10, blank=True, default="A")
    played = models.PositiveSmallIntegerField(default=0)
    won = models.PositiveSmallIntegerField(default=0)
    lost = models.PositiveSmallIntegerField(default=0)
    tied = models.PositiveSmallIntegerField(default=0)
    no_result = models.PositiveSmallIntegerField(default=0)
    points = models.PositiveSmallIntegerField(default=0)
    runs_for = models.PositiveIntegerField(default=0)
    balls_faced = models.PositiveIntegerField(default=0)
    runs_against = models.PositiveIntegerField(default=0)
    balls_bowled = models.PositiveIntegerField(default=0)
    net_run_rate = models.DecimalField(max_digits=7, decimal_places=3, default=0)
    position = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["group", "position"]
        constraints = [models.UniqueConstraint(fields=["tournament", "team"], name="uniq_points_team")]
