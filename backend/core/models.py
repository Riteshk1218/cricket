from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Append-only record of administrative and scoring actions."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    action = models.CharField(max_length=64, db_index=True)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64, blank=True)
    match = models.ForeignKey("matches.Match", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["object_type", "object_id"])]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.object_type}#{self.object_id}"


def audit(user, action, obj=None, match=None, **data):
    """Create an audit log entry. ``obj`` may be any model instance."""
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        object_type=obj._meta.model_name if obj is not None else "",
        object_id=str(obj.pk) if obj is not None else "",
        match=match,
        data=data,
    )
