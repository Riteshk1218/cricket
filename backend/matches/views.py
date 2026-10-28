from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.permissions import ReadOnlyOrAdminRole, can_manage_match, can_manage_tournament, can_score_match
from core.models import audit

from .engine import service
from .engine.snapshot import build_snapshot, commentary_entries, innings_payload
from .models import Delivery, Match, ScorerAssignment
from .serializers import (
    CorrectionSerializer, DeliveryInput, EditDeliveryInput, MatchSerializer, ScorerAssignmentSerializer,
)


def _int(value, name):
    try:
        return int(value)
    except (TypeError, ValueError):
        from core.exceptions import ScoringError

        raise ScoringError(f"'{name}' must be a player id.", "invalid")


def _opt_int(value):
    return int(value) if value not in (None, "") else None


class MatchViewSet(viewsets.ModelViewSet):
    serializer_class = MatchSerializer
    permission_classes = [ReadOnlyOrAdminRole]
    filterset_fields = ["tournament", "status", "stage", "ground"]
    ordering_fields = ["scheduled_at", "match_number"]

    def get_queryset(self):
        qs = Match.objects.select_related("tournament", "team_a", "team_b", "ground", "result")
        p = self.request.query_params
        state = p.get("state")
        if state == "live":
            qs = qs.filter(status__in=Match.LIVE_STATUSES)
        elif state == "upcoming":
            qs = qs.filter(status__in=[Match.Status.SCHEDULED, Match.Status.TOSS]).order_by("scheduled_at")
        elif state == "completed":
            qs = qs.filter(status__in=Match.FINISHED_STATUSES).order_by("-completed_at", "-scheduled_at")
        if p.get("team"):
            qs = qs.filter(Q(team_a_id=p["team"]) | Q(team_b_id=p["team"]))
        if p.get("assigned") and self.request.user.is_authenticated:
            user = self.request.user
            if user.is_super_admin:
                pass
            elif user.is_tournament_admin:
                qs = qs.filter(Q(tournament__admins=user) | Q(scorer_assignments__scorer=user, scorer_assignments__is_active=True)).distinct()
            else:
                qs = qs.filter(scorer_assignments__scorer=user, scorer_assignments__is_active=True).distinct()
        return qs

    def perform_create(self, serializer):
        tournament = serializer.validated_data["tournament"]
        if not can_manage_tournament(self.request.user, tournament):
            raise PermissionDenied("You do not manage this tournament.")
        number = serializer.validated_data.get("match_number")
        if not number or tournament.matches.filter(match_number=number).exists():
            last = tournament.matches.order_by("-match_number").values_list("match_number", flat=True).first() or 0
            serializer.validated_data["match_number"] = last + 1
        match = serializer.save(created_by=self.request.user)
        audit(self.request.user, "match.create", match, match=match)

    def perform_update(self, serializer):
        if not can_manage_match(self.request.user, serializer.instance):
            raise PermissionDenied("You do not manage this tournament.")
        match = serializer.save()
        match.version += 1
        match.save(update_fields=["version"])
        audit(self.request.user, "match.update", match, match=match)

    def perform_destroy(self, instance):
        if not can_manage_match(self.request.user, instance):
            raise PermissionDenied("You do not manage this tournament.")
        if instance.status != Match.Status.SCHEDULED:
            raise PermissionDenied("Only matches that have not started can be deleted.")
        audit(self.request.user, "match.delete", instance)
        instance.delete()

    # -- public views ------------------------------------------------------
    @action(detail=True, permission_classes=[permissions.AllowAny])
    def live(self, request, pk=None):
        return Response(build_snapshot(self.get_object()))

    @action(detail=True, permission_classes=[permissions.AllowAny])
    def commentary(self, request, pk=None):
        match = self.get_object()
        names = service.player_names(match)
        entries = []
        for inn in match.innings.order_by("number"):
            data, state, deliveries = innings_payload(inn, names)
            for e in commentary_entries(inn, names, state, deliveries):
                e["innings"] = inn.number
                entries.append(e)
        entries.sort(key=lambda e: (e["innings"], e.get("sequence", 0)), reverse=True)
        return Response(entries)

    @action(detail=True, permission_classes=[permissions.AllowAny])
    def deliveries(self, request, pk=None):
        match = self.get_object()
        rows = (Delivery.objects.filter(innings__match=match, voided=False).select_related("innings")
                .order_by("innings__number", "sequence"))
        return Response([dict(service.delivery_snapshot(d), innings=d.innings.number) for d in rows])

    # -- administration ----------------------------------------------------
    @action(detail=True, methods=["get", "post"], url_path="scorers")
    def scorers(self, request, pk=None):
        match = self.get_object()
        if request.method == "GET":
            if not (can_score_match(request.user, match)):
                raise PermissionDenied()
            return Response(ScorerAssignmentSerializer(match.scorer_assignments.select_related("scorer"), many=True).data)
        if not can_manage_match(request.user, match):
            raise PermissionDenied("You do not manage this tournament.")
        s = ScorerAssignmentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        assignment, _ = ScorerAssignment.objects.update_or_create(
            match=match, scorer=s.validated_data["scorer"],
            defaults={"is_active": s.validated_data.get("is_active", True), "assigned_by": request.user})
        audit(request.user, "scorer.assign", assignment, match=match, scorer=assignment.scorer_id,
              active=assignment.is_active)
        return Response(ScorerAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def corrections(self, request, pk=None):
        match = self.get_object()
        if not can_score_match(request.user, match):
            raise PermissionDenied()
        return Response(CorrectionSerializer(match.corrections.select_related("user"), many=True).data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def permissions_info(self, request, pk=None):
        match = self.get_object()
        return Response({"can_score": can_score_match(request.user, match),
                         "can_manage": can_manage_match(request.user, match)})

    # -- scoring -----------------------------------------------------------
    def _done(self, match_id, http_status=status.HTTP_200_OK, **extra):
        match = Match.objects.select_related("tournament", "team_a", "team_b", "ground").get(pk=match_id)
        payload = {"snapshot": build_snapshot(match)}
        payload.update(extra)
        return Response(payload, status=http_status)

    @action(detail=True, methods=["post"], url_path="score/squad", permission_classes=[permissions.IsAuthenticated])
    def score_squad(self, request, pk=None):
        service.set_squad(request.user, int(pk), _int(request.data.get("team"), "team"), request.data.get("players") or [])
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/toss", permission_classes=[permissions.IsAuthenticated])
    def score_toss(self, request, pk=None):
        service.record_toss(request.user, int(pk), _int(request.data.get("winner"), "winner"), request.data.get("decision"))
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/start-innings", permission_classes=[permissions.IsAuthenticated])
    def score_start_innings(self, request, pk=None):
        d = request.data
        service.start_innings(request.user, int(pk), _int(d.get("striker"), "striker"),
                              _opt_int(d.get("non_striker")), _int(d.get("bowler"), "bowler"))
        return self._done(pk, status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="score/delivery", permission_classes=[permissions.IsAuthenticated])
    def score_delivery(self, request, pk=None):
        s = DeliveryInput(data=request.data)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        data["client_event_id"] = str(data["client_event_id"])
        if data.get("wicket"):
            data["wicket"] = dict(data["wicket"])
        delivery, _, duplicate = service.record_delivery(request.user, int(pk), data)
        return self._done(pk, status.HTTP_200_OK if duplicate else status.HTTP_201_CREATED,
                          delivery_id=delivery.pk, duplicate=duplicate)

    @action(detail=True, methods=["post"], url_path="score/bowler", permission_classes=[permissions.IsAuthenticated])
    def score_bowler(self, request, pk=None):
        service.set_bowler(request.user, int(pk), _int(request.data.get("bowler"), "bowler"),
                           bool(request.data.get("mid_over")), request.data.get("reason", ""))
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/batter", permission_classes=[permissions.IsAuthenticated])
    def score_batter(self, request, pk=None):
        service.set_batter(request.user, int(pk), _int(request.data.get("player"), "player"),
                           request.data.get("end", "striker"))
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/swap-strike", permission_classes=[permissions.IsAuthenticated])
    def score_swap(self, request, pk=None):
        service.swap_strike(request.user, int(pk))
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/retire", permission_classes=[permissions.IsAuthenticated])
    def score_retire(self, request, pk=None):
        service.retire_batter(request.user, int(pk), _int(request.data.get("player"), "player"),
                              request.data.get("kind", "retired_hurt"))
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/undo", permission_classes=[permissions.IsAuthenticated])
    def score_undo(self, request, pk=None):
        service.undo_last(request.user, int(pk), request.data.get("reason", ""),
                          request.data.get("expected_sequence"))
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path=r"score/edit/(?P<delivery_id>\d+)",
            permission_classes=[permissions.IsAuthenticated])
    def score_edit(self, request, pk=None, delivery_id=None):
        s = EditDeliveryInput(data=request.data)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        reason = data.pop("reason", "")
        if data.get("wicket"):
            data["wicket"] = dict(data["wicket"])
        service.edit_delivery(request.user, int(pk), int(delivery_id), data, reason)
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/end-innings", permission_classes=[permissions.IsAuthenticated])
    def score_end_innings(self, request, pk=None):
        service.end_innings(request.user, int(pk), request.data.get("reason", "declared"))
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/pause", permission_classes=[permissions.IsAuthenticated])
    def score_pause(self, request, pk=None):
        service.pause_match(request.user, int(pk), request.data.get("reason", ""))
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/resume", permission_classes=[permissions.IsAuthenticated])
    def score_resume(self, request, pk=None):
        service.resume_match(request.user, int(pk))
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/revise", permission_classes=[permissions.IsAuthenticated])
    def score_revise(self, request, pk=None):
        service.revise_innings(request.user, int(pk), request.data.get("max_overs"), request.data.get("target"),
                               request.data.get("reason", ""))
        return self._done(pk)

    @action(detail=True, methods=["post"], url_path="score/finish", permission_classes=[permissions.IsAuthenticated])
    def score_finish(self, request, pk=None):
        d = request.data
        service.finish_match(request.user, int(pk), d.get("kind") or None, _opt_int(d.get("winner")),
                             _opt_int(d.get("player_of_match")), d.get("summary", ""))
        return self._done(pk)
