from datetime import time

from django.db.models import Count, Q
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.permissions import ReadOnlyOrAdminRole, can_manage_tournament, is_admin_user
from core.models import audit

from .models import Ground, Player, Team, Tournament, TournamentRegistration
from .serializers import (
    GroundSerializer, PlayerSerializer, PointsTableSerializer, RegistrationSerializer, TeamSerializer,
    TournamentSerializer,
)
from .services import generate_knockout_round, generate_league_fixtures, recompute_points_table


class OwnedEditMixin:
    """Admins may create; editing is limited to Super Admins or the record's creator."""

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method in permissions.SAFE_METHODS:
            return
        user = request.user
        if user.is_super_admin:
            return
        if getattr(obj, "created_by_id", None) != user.pk:
            raise PermissionDenied("Only the creator or a Super Admin can change this record.")

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        audit(self.request.user, f"{obj._meta.model_name}.create", obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        audit(self.request.user, f"{obj._meta.model_name}.update", obj)


class GroundViewSet(OwnedEditMixin, viewsets.ModelViewSet):
    queryset = Ground.objects.all()
    serializer_class = GroundSerializer
    permission_classes = [ReadOnlyOrAdminRole]
    search_fields = ["name", "city"]
    pagination_class = None


class TeamViewSet(OwnedEditMixin, viewsets.ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [ReadOnlyOrAdminRole]
    search_fields = ["name", "short_name", "city"]
    filterset_fields = ["registrations__tournament"]

    def get_queryset(self):
        return Team.objects.annotate(player_count=Count("players")).order_by("name")

    @action(detail=True)
    def players(self, request, pk=None):
        team = self.get_object()
        return Response(PlayerSerializer(team.players.all(), many=True, context={"request": request}).data)


class PlayerViewSet(OwnedEditMixin, viewsets.ModelViewSet):
    queryset = Player.objects.select_related("team")
    serializer_class = PlayerSerializer
    permission_classes = [ReadOnlyOrAdminRole]
    search_fields = ["full_name", "short_name"]
    filterset_fields = ["team", "role"]


class TournamentViewSet(viewsets.ModelViewSet):
    serializer_class = TournamentSerializer
    permission_classes = [ReadOnlyOrAdminRole]
    search_fields = ["name", "location"]
    filterset_fields = ["status", "kind", "match_format", "ball_type"]
    ordering_fields = ["start_date", "name"]

    def get_queryset(self):
        qs = Tournament.objects.annotate(
            team_count=Count("registrations", distinct=True),
            match_count=Count("matches", distinct=True),
            live_count=Count("matches", filter=Q(matches__status__in=["live", "innings_break", "paused"]), distinct=True),
        ).prefetch_related("grounds", "admins").select_related("winner", "runner_up")
        if self.request.query_params.get("managed") and self.request.user.is_authenticated:
            if not self.request.user.is_super_admin:
                qs = qs.filter(admins=self.request.user)
        return qs

    def _require_manage(self, tournament):
        if not can_manage_tournament(self.request.user, tournament):
            raise PermissionDenied("You do not manage this tournament.")

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in permissions.SAFE_METHODS:
            self._require_manage(obj)

    def perform_create(self, serializer):
        user = self.request.user
        admins = serializer.validated_data.get("admins")
        if admins is not None and not user.is_super_admin:
            serializer.validated_data.pop("admins")
        tournament = serializer.save(created_by=user)
        if not user.is_super_admin:
            tournament.admins.add(user)
        audit(user, "tournament.create", tournament)

    def perform_update(self, serializer):
        if "admins" in serializer.validated_data and not self.request.user.is_super_admin:
            serializer.validated_data.pop("admins")
        tournament = serializer.save()
        audit(self.request.user, "tournament.update", tournament)

    def perform_destroy(self, instance):
        if not self.request.user.is_super_admin:
            raise PermissionDenied("Only a Super Admin can delete a tournament.")
        audit(self.request.user, "tournament.delete", instance, name=instance.name)
        instance.delete()

    @action(detail=True, methods=["get", "post"], permission_classes=[permissions.AllowAny])
    def registrations(self, request, pk=None):
        tournament = self.get_object()
        if request.method == "GET":
            qs = tournament.registrations.select_related("team").prefetch_related("players")
            return Response(RegistrationSerializer(qs, many=True, context={"request": request}).data)
        self._require_manage(tournament)
        s = RegistrationSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        if tournament.registrations.filter(team=s.validated_data["team"]).exists():
            return Response({"detail": "This team is already registered."}, status=status.HTTP_400_BAD_REQUEST)
        players = s.validated_data.pop("players", None)
        reg = s.save(tournament=tournament)
        reg.players.set(players if players is not None else reg.team.players.all())
        recompute_points_table(tournament)
        audit(request.user, "registration.create", reg, tournament=tournament.pk)
        return Response(RegistrationSerializer(reg, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def generate_fixtures(self, request, pk=None):
        tournament = self.get_object()
        self._require_manage(tournament)
        data = request.data
        start = parse_date(str(data.get("start_date"))) if data.get("start_date") else None
        first = parse_time(str(data.get("first_start"))) if data.get("first_start") else time(9, 0)
        created = generate_league_fixtures(
            tournament, request.user, start_date=start, matches_per_day=int(data.get("matches_per_day") or 4),
            first_start=first, slot_hours=int(data.get("slot_hours") or 3),
            double_round=bool(data.get("double_round")), replace=bool(data.get("replace")),
        )
        audit(request.user, "fixtures.generate", tournament, count=len(created))
        return Response({"created": len(created)}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def generate_knockouts(self, request, pk=None):
        tournament = self.get_object()
        self._require_manage(tournament)
        start = parse_datetime(str(request.data.get("start_at"))) if request.data.get("start_at") else None
        created = generate_knockout_round(tournament, request.user, start)
        audit(request.user, "fixtures.knockout", tournament, matches=[m.pk for m in created])
        return Response({"created": [m.pk for m in created]}, status=status.HTTP_201_CREATED)

    @action(detail=True, permission_classes=[permissions.AllowAny])
    def points_table(self, request, pk=None):
        tournament = self.get_object()
        rows = tournament.points_table.select_related("team").order_by("group", "position")
        if not rows.exists() and tournament.registrations.exists():
            recompute_points_table(tournament)
            rows = tournament.points_table.select_related("team").order_by("group", "position")
        return Response(PointsTableSerializer(rows, many=True, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        tournament = self.get_object()
        self._require_manage(tournament)
        recompute_points_table(tournament)
        return Response({"ok": True})


class RegistrationViewSet(viewsets.ModelViewSet):
    """Edit or remove a team registration (squad changes)."""

    serializer_class = RegistrationSerializer
    queryset = TournamentRegistration.objects.select_related("team", "tournament").prefetch_related("players")
    permission_classes = [ReadOnlyOrAdminRole]
    filterset_fields = ["tournament", "team"]
    http_method_names = ["get", "patch", "put", "delete"]

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in permissions.SAFE_METHODS and not can_manage_tournament(request.user, obj.tournament):
            raise PermissionDenied("You do not manage this tournament.")

    def perform_update(self, serializer):
        reg = serializer.save()
        recompute_points_table(reg.tournament)
        audit(self.request.user, "registration.update", reg)

    def perform_destroy(self, instance):
        if instance.tournament.matches.filter(Q(team_a=instance.team) | Q(team_b=instance.team)).exists():
            raise PermissionDenied("This team already has fixtures in the tournament.")
        tournament = instance.tournament
        audit(self.request.user, "registration.delete", instance)
        instance.delete()
        recompute_points_table(tournament)
