"""ASGI entry point: HTTP via Django, WebSockets via Channels."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import OriginValidator  # noqa: E402

from matches.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # Live feeds are public and read-only; any origin on the local network may connect.
    "websocket": OriginValidator(URLRouter(websocket_urlpatterns), ["*"]),
})
