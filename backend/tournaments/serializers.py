from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.cricket_rules import default_rules, normalize_rules

from .models import Ground, Player, PointsTableEntry, Team, Tournament, TournamentRegistration

User = get_user_model()


class GroundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ground
        fields = ["id", "name", "city", "address", "capacity"]


class TeamSerializer(serializers.ModelSerializer):
    player_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Team
        fields = ["id", "name", "short_name", "logo", "primary_color", "city", "player_count"]

    def validate_short_name(self, value):
        return value.upper()[:6]

    def validate_primary_color(self, value):
        import re

        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise serializers.ValidationError("Use a hex colour like #0f766e.")
        return value


class PlayerSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True, default=None)

    class Meta:
        model = Player
        fields = ["id", "full_name", "short_name", "team", "team_name", "role", "batting_style", "bowling_style",
                  "jersey_number", "date_of_birth", "photo"]


class TournamentSerializer(serializers.ModelSerializer):
    admins = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), required=False)
    grounds = serializers.PrimaryKeyRelatedField(many=True, queryset=Ground.objects.all(), required=False)
    ground_details = GroundSerializer(source="grounds", many=True, read_only=True)
    winner_name = serializers.CharField(source="winner.name", read_only=True, default=None)
    runner_up_name = serializers.CharField(source="runner_up.name", read_only=True, default=None)
    team_count = serializers.IntegerField(read_only=True, required=False)
    match_count = serializers.IntegerField(read_only=True, required=False)
    live_count = serializers.IntegerField(read_only=True, required=False)
    overs = serializers.IntegerField(write_only=True, required=False, min_value=1, max_value=100)

    class Meta:
        model = Tournament
        fields = [
            "id", "name", "slug", "short_name", "logo", "location", "start_date", "end_date", "kind",
            "match_format", "ball_type", "rules", "overs", "points_win", "points_tie", "points_no_result",
            "points_loss", "playoff_teams", "status", "winner", "winner_name", "runner_up", "runner_up_name",
            "grounds", "ground_details", "admins", "description", "team_count", "match_count", "live_count",
            "created_at",
        ]
        read_only_fields = ["slug", "winner", "runner_up", "created_at"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date must be on or after the start date."})
        overs = attrs.pop("overs", None)
        fmt = attrs.get("match_format", getattr(self.instance, "match_format", "T20"))
        ball = attrs.get("ball_type", getattr(self.instance, "ball_type", "leather"))
        if "rules" in attrs or overs or self.instance is None or "match_format" in attrs or "ball_type" in attrs:
            base = default_rules(fmt, ball, overs)
            if self.instance is not None and "match_format" not in attrs and "ball_type" not in attrs and not overs:
                base = dict(self.instance.rules)
            base.update(attrs.get("rules") or {})
            from django.core.exceptions import ValidationError

            try:
                attrs["rules"] = normalize_rules(base)
            except ValidationError as exc:
                raise serializers.ValidationError({"rules": exc.message_dict})
        return attrs


class RegistrationSerializer(serializers.ModelSerializer):
    team_detail = TeamSerializer(source="team", read_only=True)
    players = serializers.PrimaryKeyRelatedField(many=True, queryset=Player.objects.all(), required=False)

    class Meta:
        model = TournamentRegistration
        fields = ["id", "tournament", "team", "team_detail", "group", "seed", "players", "registered_at"]
        read_only_fields = ["tournament", "registered_at"]

    def validate_players(self, players):
        team = self.initial_data.get("team") or getattr(self.instance, "team_id", None)
        wrong = [p.full_name for p in players if p.team_id and team and p.team_id != int(team)]
        if wrong:
            raise serializers.ValidationError(f"These players belong to another team: {', '.join(wrong)}")
        return players


class PointsTableSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)

    class Meta:
        model = PointsTableEntry
        fields = ["position", "group", "team", "played", "won", "lost", "tied", "no_result", "points",
                  "runs_for", "balls_faced", "runs_against", "balls_bowled", "net_run_rate"]
