import hashlib
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import LiveConnection, PageView


def visitor_hash(raw_id, day):
    """Hash a client-generated random ID with a server salt and the date.

    The same browser counts as one unique visitor per day, but visits cannot be
    linked across days and the raw ID is never stored.
    """
    payload = f"{settings.ANALYTICS_SALT}:{day.isoformat()}:{raw_id}".encode()
    return hashlib.sha256(payload).hexdigest()


def record_page_view(path, visitor_id, client="web", match=None, user=None):
    today = timezone.localdate()
    return PageView.objects.create(
        path=path[:200], match=match, client=client, day=today,
        visitor_hash=visitor_hash(visitor_id or "anonymous", today),
        is_authenticated=bool(user and user.is_authenticated),
    )


def _fresh():
    return LiveConnection.objects.filter(
        last_seen__gte=timezone.now() - timedelta(seconds=settings.LIVE_CONNECTION_STALE_SECONDS))


def viewers_for_match(match_id):
    return _fresh().filter(match_id=match_id).count()


def register_connection(channel_name, match_id, client):
    LiveConnection.objects.update_or_create(channel_name=channel_name, defaults={"match_id": match_id, "client": client})
    return viewers_for_match(match_id) if match_id else None


def unregister_connection(channel_name, match_id):
    LiveConnection.objects.filter(channel_name=channel_name).delete()
    return viewers_for_match(match_id) if match_id else None


def heartbeat(channel_name):
    LiveConnection.objects.filter(channel_name=channel_name).update(last_seen=timezone.now())


def purge_stale_connections():
    cutoff = timezone.now() - timedelta(seconds=settings.LIVE_CONNECTION_STALE_SECONDS * 4)
    return LiveConnection.objects.filter(last_seen__lt=cutoff).delete()[0]


def current_connections():
    return _fresh()
