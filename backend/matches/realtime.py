"""Push match updates to WebSocket viewers.

Each match has its own channel group (``match_<id>``), so an update for one
match is only ever delivered to viewers of that match. A separate
``live_scores`` group receives compact summaries for the home page ticker.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

LIVE_GROUP = "live_scores"


def match_group(match_id):
    return f"match_{int(match_id)}"


def broadcast_match(match_id, version):
    from .engine.snapshot import build_snapshot, match_summary
    from .models import Match

    layer = get_channel_layer()
    if layer is None:
        return
    try:
        match = Match.objects.select_related("tournament", "team_a", "team_b", "ground").get(pk=match_id)
    except Match.DoesNotExist:
        return
    if match.version != version:
        # A newer change already committed; its own broadcast will follow.
        return
    snapshot = build_snapshot(match)
    latest = next((c for c in snapshot["commentary"] if c["type"] == "ball"), None)
    try:
        async_to_sync(layer.group_send)(match_group(match_id), {
            "type": "match.update", "snapshot": snapshot, "event": latest,
        })
        async_to_sync(layer.group_send)(LIVE_GROUP, {"type": "live.summary", "summary": match_summary(match)})
    except Exception:  # pragma: no cover - a broken channel layer must not break scoring
        logger.exception("Failed to broadcast match %s", match_id)


def broadcast_viewers(match_id, count):
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(match_group(match_id), {"type": "viewers.update", "count": count})
