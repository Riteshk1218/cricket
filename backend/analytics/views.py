from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUserRole
from matches.models import Delivery, Match
from tournaments.models import Player, Team, Tournament

from .models import PageView
from .serializers import TrackSerializer
from .services import current_connections, purge_stale_connections, record_page_view

User = get_user_model()


class TrackView(APIView):
    """Anonymous page/screen view beacon used by the website and the apps."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        s = TrackSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        match = Match.objects.filter(pk=s.validated_data.get("match")).first() if s.validated_data.get("match") else None
        record_page_view(s.validated_data["path"], s.validated_data["visitor_id"], s.validated_data["client"], match)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardView(APIView):
    """Platform analytics for Super Admins (all data) and Tournament Admins (their tournaments)."""

    permission_classes = [IsAdminUserRole]

    def get(self, request):
        purge_stale_connections()
        user = request.user
        tournaments = Tournament.objects.all()
        if not user.is_super_admin:
            tournaments = tournaments.filter(admins=user)
        matches = Match.objects.filter(tournament__in=tournaments)
        today = timezone.localdate()
        views = PageView.objects.all()
        if not user.is_super_admin:
            views = views.filter(match__in=matches)

        conns = current_connections()
        if not user.is_super_admin:
            conns = conns.filter(match__in=matches)
        per_match = (conns.exclude(match=None).values("match").annotate(viewers=Count("id")).order_by("-viewers"))
        match_names = {m.pk: str(m) for m in Match.objects.filter(pk__in=[r["match"] for r in per_match]).select_related("team_a", "team_b")}

        start = today - timedelta(days=29)
        daily_rows = (views.filter(day__gte=start).values("day")
                      .annotate(page_views=Count("id"), unique_visitors=Count("visitor_hash", distinct=True)))
        daily_map = {r["day"]: r for r in daily_rows}
        daily = []
        for i in range(30):
            d = start + timedelta(days=i)
            row = daily_map.get(d, {})
            daily.append({"date": d.isoformat(), "page_views": row.get("page_views", 0),
                          "unique_visitors": row.get("unique_visitors", 0)})
        month_start = (today.replace(day=1) - timedelta(days=330)).replace(day=1)
        monthly = [
            {"month": r["month"].strftime("%Y-%m"), "page_views": r["page_views"]}
            for r in views.filter(day__gte=month_start).annotate(month=TruncMonth("day")).values("month")
            .annotate(page_views=Count("id")).order_by("month")
        ]
        # Unique visitors in a month cannot be summed from daily hashes (hashes rotate daily),
        # so monthly figures report visitor-days instead.
        for row in monthly:
            row["visitor_days"] = (views.filter(day__year=int(row["month"][:4]), day__month=int(row["month"][5:]))
                                   .values("day", "visitor_hash").distinct().count())
        popular = (views.exclude(match=None).values("match").annotate(views=Count("id")).order_by("-views")[:10])
        popular_names = {m.pk: m for m in Match.objects.filter(pk__in=[r["match"] for r in popular]).select_related("team_a", "team_b", "tournament")}
        active_window = timezone.now() - timedelta(minutes=30)
        active_scorers = (Delivery.objects.filter(created_at__gte=active_window, innings__match__in=matches)
                          .values("created_by").distinct().count())
        android_today = views.filter(client="android", day=today)

        data = {
            "totals": {
                "users": User.objects.count() if user.is_super_admin else None,
                "tournaments": tournaments.count(),
                "teams": Team.objects.filter(registrations__tournament__in=tournaments).distinct().count()
                if not user.is_super_admin else Team.objects.count(),
                "players": Player.objects.count() if user.is_super_admin else
                Player.objects.filter(tournament_registrations__tournament__in=tournaments).distinct().count(),
                "matches": matches.count(),
                "live_matches": matches.filter(status__in=Match.LIVE_STATUSES).count(),
                "completed_matches": matches.filter(status__in=Match.FINISHED_STATUSES).count(),
                "upcoming_matches": matches.filter(status__in=[Match.Status.SCHEDULED, Match.Status.TOSS]).count(),
                "active_scorers": active_scorers,
            },
            "realtime": {
                "current_connections": conns.count(),
                "by_client": {r["client"]: r["n"] for r in conns.values("client").annotate(n=Count("id"))},
                "viewers_per_match": [
                    {"match": r["match"], "title": match_names.get(r["match"], ""), "viewers": r["viewers"]}
                    for r in per_match
                ],
            },
            "traffic": {
                "page_views_today": views.filter(day=today).count(),
                "unique_visitors_today": views.filter(day=today).values("visitor_hash").distinct().count(),
                "page_views_total": views.count(),
                "match_views_total": views.exclude(match=None).count(),
                "daily": daily,
                "monthly": monthly,
                "by_client": {r["client"]: r["n"] for r in views.values("client").annotate(n=Count("id"))},
            },
            "android": {
                "screen_views_today": android_today.count(),
                "unique_devices_today": android_today.values("visitor_hash").distinct().count(),
                "screen_views_30d": views.filter(client="android", day__gte=start).count(),
                "live_connections": conns.filter(client="android").count(),
            },
            "popular_matches": [
                {"match": r["match"], "views": r["views"],
                 "title": str(popular_names[r["match"]]) if r["match"] in popular_names else "",
                 "tournament": popular_names[r["match"]].tournament.name if r["match"] in popular_names else ""}
                for r in popular
            ],
            "definitions": {
                "current_connections": "Open WebSocket connections right now (one browser tab or app screen each).",
                "unique_visitors": "Distinct anonymous visitor IDs per day (IDs are salted and rotate daily).",
                "page_views": "Every page or screen opened, including repeat views by the same visitor.",
            },
        }
        return Response(data)
