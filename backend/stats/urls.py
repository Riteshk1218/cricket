from django.urls import path

from .views import LeaderboardView, PlayerStatsView, TeamStatsView

urlpatterns = [
    path("stats/players/<int:player_id>/", PlayerStatsView.as_view(), name="player-stats"),
    path("stats/teams/<int:team_id>/", TeamStatsView.as_view(), name="team-stats"),
    path("stats/leaderboards/", LeaderboardView.as_view(), name="leaderboards"),
]
