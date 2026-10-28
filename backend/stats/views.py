from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from matches.models import Innings, Match, MatchResult
from tournaments.models import Player, Team

from .services import leaderboards, player_stats


class PlayerStatsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, player_id):
        player = get_object_or_404(Player.objects.select_related("team"), pk=player_id)
        tournament = request.query_params.get("tournament")
        data = player_stats(player.pk, int(tournament) if tournament else None)
        recent = []
        for inn in (Innings.objects.filter(Q(deliveries__striker=player) | Q(deliveries__bowler=player),
                                           deliveries__voided=False, is_super_over=False)
                    .select_related("match__team_a", "match__team_b", "match__tournament").distinct()
                    .order_by("-match__scheduled_at")[:10]):
            agg = inn.deliveries.filter(voided=False, striker=player).aggregate(
                runs=Sum("runs_bat"), balls=Count("id", filter=Q(wides=0, is_penalty_only=False)))
            bowl = inn.deliveries.filter(voided=False, bowler=player).aggregate(
                balls=Count("id", filter=Q(wides=0, noballs=0, is_penalty_only=False)))
            recent.append({
                "match_id": inn.match_id, "match": str(inn.match), "tournament": inn.match.tournament.name,
                "date": inn.match.scheduled_at.date().isoformat(), "innings": inn.number,
                "runs": agg["runs"] or 0, "balls": agg["balls"], "bowled_balls": bowl["balls"],
                "wickets": inn.dismissals.filter(voided=False, bowler=player).count(),
            })
        return Response({
            "player": {"id": player.pk, "full_name": player.full_name, "short_name": player.short_name,
                       "team": player.team_id, "team_name": player.team.name if player.team else None,
                       "role": player.role, "batting_style": player.batting_style,
                       "bowling_style": player.bowling_style,
                       "photo": request.build_absolute_uri(player.photo.url) if player.photo else None},
            "stats": data,
            "recent": recent,
        })


class LeaderboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        t = request.query_params.get("tournament")
        return Response(leaderboards(int(t) if t else None))


class TeamStatsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, team_id):
        team = get_object_or_404(Team, pk=team_id)
        played = Match.objects.filter(Q(team_a=team) | Q(team_b=team), status__in=Match.FINISHED_STATUSES)
        results = MatchResult.objects.filter(match__in=played)
        won = results.filter(winner=team).count()
        no_result = results.filter(kind__in=["no_result", "abandoned"]).count()
        tied = results.filter(kind="tie").count()
        highest = Innings.objects.filter(batting_team=team, is_super_over=False).order_by("-total_runs").first()
        return Response({
            "team": team.pk, "played": played.count(), "won": won, "tied": tied, "no_result": no_result,
            "lost": played.count() - won - tied - no_result,
            "highest_total": {"runs": highest.total_runs, "wickets": highest.wickets, "match": highest.match_id}
            if highest else None,
        })
