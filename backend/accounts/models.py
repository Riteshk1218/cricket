from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        TOURNAMENT_ADMIN = "tournament_admin", "Tournament Admin"
        SCORER = "scorer", "Scorer"
        VIEWER = "viewer", "Viewer"

    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        HINDI = "hi", "Hindi"
        MARATHI = "mr", "Marathi"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.VIEWER, db_index=True)
    display_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(max_length=2, choices=Language.choices, default=Language.ENGLISH)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    REQUIRED_FIELDS = ["email"]

    @property
    def is_super_admin(self):
        return self.is_superuser or self.role == self.Role.SUPER_ADMIN

    @property
    def is_tournament_admin(self):
        return self.role == self.Role.TOURNAMENT_ADMIN

    @property
    def is_scorer(self):
        return self.role == self.Role.SCORER

    def save(self, *args, **kwargs):
        # Django superusers created from the CLI are always Super Admins.
        if self.is_superuser:
            self.role = self.Role.SUPER_ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or self.username


class UserFavorite(models.Model):
    """A viewer's followed team, match or tournament. Exactly one target is set."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    team = models.ForeignKey("tournaments.Team", null=True, blank=True, on_delete=models.CASCADE, related_name="followers")
    match = models.ForeignKey("matches.Match", null=True, blank=True, on_delete=models.CASCADE, related_name="followers")
    tournament = models.ForeignKey("tournaments.Tournament", null=True, blank=True, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="favorite_exactly_one_target",
                condition=(
                    Q(team__isnull=False, match__isnull=True, tournament__isnull=True)
                    | Q(team__isnull=True, match__isnull=False, tournament__isnull=True)
                    | Q(team__isnull=True, match__isnull=True, tournament__isnull=False)
                ),
            ),
            models.UniqueConstraint(fields=["user", "team"], condition=Q(team__isnull=False), name="uniq_fav_team"),
            models.UniqueConstraint(fields=["user", "match"], condition=Q(match__isnull=False), name="uniq_fav_match"),
            models.UniqueConstraint(fields=["user", "tournament"], condition=Q(tournament__isnull=False), name="uniq_fav_tournament"),
        ]
