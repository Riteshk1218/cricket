from django.urls import path

from .views import DashboardView, TrackView

urlpatterns = [
    path("analytics/track/", TrackView.as_view(), name="analytics-track"),
    path("analytics/dashboard/", DashboardView.as_view(), name="analytics-dashboard"),
]
