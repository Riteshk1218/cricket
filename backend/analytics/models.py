from django.db import models


class PageView(models.Model):
    """One page or screen view. Stores a salted, day-scoped visitor hash, never an IP address."""

    class Client(models.TextChoices):
        WEB = "web", "Website"
        ANDROID = "android", "Android app"
        IOS = "ios", "iOS app"

    path = models.CharField(max_length=200)
    match = models.ForeignKey("matches.Match", null=True, blank=True, on_delete=models.SET_NULL, related_name="page_views")
    visitor_hash = models.CharField(max_length=64, db_index=True)
    client = models.CharField(max_length=8, choices=Client.choices, default=Client.WEB)
    is_authenticated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    day = models.DateField(db_index=True)

    class Meta:
        indexes = [models.Index(fields=["day", "client"]), models.Index(fields=["match", "day"])]


class LiveConnection(models.Model):
    """An open WebSocket connection. Rows are removed on disconnect and expire if heartbeats stop."""

    channel_name = models.CharField(max_length=200, unique=True)
    match = models.ForeignKey("matches.Match", null=True, blank=True, on_delete=models.CASCADE, related_name="live_connections")
    client = models.CharField(max_length=8, default="web")
    connected_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True, db_index=True)
