from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse, Http404, JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve

from core.views import AuditLogList


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/audit/", AuditLogList.as_view(), name="audit-log"),
    path("api/", include("accounts.urls")),
    path("api/", include("tournaments.urls")),
    path("api/", include("matches.urls")),
    path("api/", include("stats.urls")),
    path("api/", include("analytics.urls")),
]

def website(request):
    """Return the website's index.html for page URLs like /matches/5 (React handles routing)."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        raise Http404("Website not built")
    return FileResponse(open(index, "rb"), content_type="text/html")


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]

if (settings.FRONTEND_DIST / "index.html").exists():
    urlpatterns += [re_path(r"^(?!api/|admin/|ws/|media/|static/).*$", website)]
