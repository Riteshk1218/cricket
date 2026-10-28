from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.cricket_rules import normalize_rules

from .engine.snapshot import match_summary
from .models import Match, ScorerAssignment, ScoringCorrection


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = ["id", "tournament", "match_number", "stage", "knockout_round", "group", "team_a", "team_b",
                  "ground", "scheduled_at", "status", "rules", "version"]
        read_only_fields = ["status", "version"]

    def validate(self, attrs):
        a = attrs.get("team_a", getattr(self.instance, "team_a", None))
        b = attrs.get("team_b", getattr(self.instance, "team_b", None))
        tournament = attrs.get("tournament", getattr(self.instance, "tournament", None))
        if a and b and a == b:
            raise serializers.ValidationError("A team cannot play itself.")
        if self.instance and self.instance.status != Match.Status.SCHEDULED:
            locked = {"team_a", "team_b", "tournament", "rules"} & set(attrs)
            changed = [k for k in locked if attrs[k] != getattr(self.instance, k)]
            if changed:
                raise serializers.ValidationError("Teams, tournament and rules cannot change after the match starts.")
        if tournament and a and b:
            registered = set(tournament.registrations.values_list("team_id", flat=True))
            if registered and not {a.pk, b.pk} <= registered:
                raise serializers.ValidationError("Both teams must be registered in the tournament.")
        if "rules" in attrs or self.instance is None:
            base = dict(tournament.rules) if tournament else {}
            if self.instance is not None:
                base = dict(self.instance.rules)
            base.update(attrs.get("rules") or {})
            try:
                attrs["rules"] = normalize_rules(base)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"rules": exc.message_dict})
        return attrs

    def to_representation(self, instance):
        data = match_summary(instance)
        data["rules"] = instance.rules
        data["ground_id"] = instance.ground_id
        data["group"] = instance.group
        data["toss_winner"] = instance.toss_winner_id
        data["toss_decision"] = instance.toss_decision
        return data


class ScorerAssignmentSerializer(serializers.ModelSerializer):
    scorer_name = serializers.CharField(source="scorer.__str__", read_only=True)
    username = serializers.CharField(source="scorer.username", read_only=True)

    class Meta:
        model = ScorerAssignment
        fields = ["id", "match", "scorer", "scorer_name", "username", "is_active", "assigned_at"]
        read_only_fields = ["match", "assigned_at"]

    def validate_scorer(self, user):
        if user.role not in ("scorer", "tournament_admin", "super_admin") or not user.is_active:
            raise serializers.ValidationError("Only active scorer or admin accounts can be assigned.")
        return user


class CorrectionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.__str__", read_only=True, default=None)

    class Meta:
        model = ScoringCorrection
        fields = ["id", "action", "innings", "delivery", "before", "after", "reason", "user", "user_name", "created_at"]


class WicketInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=[
        "bowled", "caught", "caught_and_bowled", "lbw", "run_out", "stumped", "hit_wicket",
        "obstructing_field", "hit_ball_twice"])
    player_out = serializers.IntegerField(required=False, allow_null=True)
    fielder = serializers.IntegerField(required=False, allow_null=True)


class DeliveryInput(serializers.Serializer):
    client_event_id = serializers.UUIDField()
    expected_sequence = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    runs_bat = serializers.IntegerField(default=0, min_value=0, max_value=7)
    extra_type = serializers.ChoiceField(choices=["", "wide", "noball", "bye", "legbye", "penalty"], default="", allow_blank=True)
    extra_runs = serializers.IntegerField(default=0, min_value=0, max_value=7)
    noball_runs_type = serializers.ChoiceField(choices=["bat", "bye", "legbye"], default="bat")
    penalty_runs = serializers.IntegerField(default=0, min_value=0, max_value=10)
    boundary = serializers.BooleanField(required=False, allow_null=True, default=None)
    batters_crossed = serializers.BooleanField(required=False, allow_null=True, default=None)
    wicket = WicketInput(required=False, allow_null=True)
    shot_zone = serializers.CharField(required=False, allow_blank=True, max_length=12)
    note = serializers.CharField(required=False, allow_blank=True, max_length=200)


class EditDeliveryInput(serializers.Serializer):
    runs_bat = serializers.IntegerField(required=False, min_value=0, max_value=7)
    extra_type = serializers.ChoiceField(choices=["", "wide", "noball", "bye", "legbye", "penalty"], required=False, allow_blank=True)
    extra_runs = serializers.IntegerField(required=False, min_value=0, max_value=7)
    noball_runs_type = serializers.ChoiceField(choices=["bat", "bye", "legbye"], required=False)
    penalty_runs = serializers.IntegerField(required=False, min_value=0, max_value=10)
    boundary = serializers.BooleanField(required=False, allow_null=True)
    batters_crossed = serializers.BooleanField(required=False, allow_null=True)
    wicket = WicketInput(required=False, allow_null=True)
    striker = serializers.IntegerField(required=False)
    non_striker = serializers.IntegerField(required=False)
    bowler = serializers.IntegerField(required=False)
    shot_zone = serializers.CharField(required=False, allow_blank=True, max_length=12)
    note = serializers.CharField(required=False, allow_blank=True, max_length=200)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
