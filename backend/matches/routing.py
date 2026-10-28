from django.urls import path

from .consumers import LiveScoresConsumer, MatchConsumer

websocket_urlpatterns = [
    path("ws/matches/<int:match_id>/", MatchConsumer.as_asgi()),
    path("ws/live/", LiveScoresConsumer.as_asgi()),
]
