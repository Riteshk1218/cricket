from rest_framework import generics, serializers

from accounts.permissions import IsSuperAdmin

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.__str__", default=None, read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "created_at", "user", "user_name", "action", "object_type", "object_id", "match", "data"]


class AuditLogList(generics.ListAPIView):
    """Read-only audit trail for Super Admins."""

    serializer_class = AuditLogSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ["action", "match", "user", "object_type"]
    search_fields = ["action", "object_type"]
    queryset = AuditLog.objects.select_related("user")
