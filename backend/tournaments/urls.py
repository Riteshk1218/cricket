from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("tournaments", views.TournamentViewSet, basename="tournament")
router.register("registrations", views.RegistrationViewSet, basename="registration")
router.register("grounds", views.GroundViewSet, basename="ground")
router.register("teams", views.TeamViewSet, basename="team")
router.register("players", views.PlayerViewSet, basename="player")

urlpatterns = [path("", include(router.urls))]
