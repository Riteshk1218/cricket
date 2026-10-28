from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .realtime import LIVE_GROUP, match_group


class MatchConsumer(AsyncJsonWebsocketConsumer):
    """Read-only live feed for one match. Scoring itself goes through the REST API."""

    async def connect(self):
        self.match_id = int(self.scope["url_route"]["kwargs"]["match_id"])
        self.group = match_group(self.match_id)
        snapshot = await self._snapshot()
        if snapshot is None:
            await self.close(code=4404)
            return
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        client = _client_type(self.scope)
        count = await self._register(client)
        await self.send_json({"type": "snapshot", "snapshot": snapshot, "viewers": count})
        await self.channel_layer.group_send(self.group, {"type": "viewers.update", "count": count})

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)
            count = await self._unregister()
            await self.channel_layer.group_send(self.group, {"type": "viewers.update", "count": count})

    async def receive_json(self, content, **kwargs):
        kind = content.get("type")
        if kind == "ping":
            await self._heartbeat()
            await self.send_json({"type": "pong"})
        elif kind == "resync":
            await self.send_json({"type": "snapshot", "snapshot": await self._snapshot()})

    async def match_update(self, event):
        await self.send_json({"type": "update", "snapshot": event["snapshot"], "event": event.get("event")})

    async def viewers_update(self, event):
        await self.send_json({"type": "viewers", "count": event["count"]})

    @database_sync_to_async
    def _snapshot(self):
        from .engine.snapshot import build_snapshot
        from .models import Match

        try:
            match = Match.objects.select_related("tournament", "team_a", "team_b", "ground").get(pk=self.match_id)
        except Match.DoesNotExist:
            return None
        return build_snapshot(match)

    @database_sync_to_async
    def _register(self, client):
        from analytics.services import register_connection

        return register_connection(self.channel_name, self.match_id, client)

    @database_sync_to_async
    def _unregister(self):
        from analytics.services import unregister_connection

        return unregister_connection(self.channel_name, self.match_id)

    @database_sync_to_async
    def _heartbeat(self):
        from analytics.services import heartbeat

        heartbeat(self.channel_name)


class LiveScoresConsumer(AsyncJsonWebsocketConsumer):
    """Compact updates for every match, used by the home page and app dashboard."""

    async def connect(self):
        await self.channel_layer.group_add(LIVE_GROUP, self.channel_name)
        await self.accept()
        await self._register(_client_type(self.scope))

    async def disconnect(self, code):
        await self.channel_layer.group_discard(LIVE_GROUP, self.channel_name)
        await self._unregister()

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self._heartbeat()
            await self.send_json({"type": "pong"})

    async def live_summary(self, event):
        await self.send_json({"type": "summary", "summary": event["summary"]})

    @database_sync_to_async
    def _register(self, client):
        from analytics.services import register_connection

        return register_connection(self.channel_name, None, client)

    @database_sync_to_async
    def _unregister(self):
        from analytics.services import unregister_connection

        return unregister_connection(self.channel_name, None)

    @database_sync_to_async
    def _heartbeat(self):
        from analytics.services import heartbeat

        heartbeat(self.channel_name)


def _client_type(scope):
    from urllib.parse import parse_qs

    qs = parse_qs(scope.get("query_string", b"").decode())
    client = (qs.get("client") or ["web"])[0]
    return client if client in ("web", "android", "ios") else "web"
