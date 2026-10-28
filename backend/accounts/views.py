from django.contrib.auth import get_user_model
from rest_framework import generics, mixins, permissions, viewsets
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from core.models import audit

from .models import UserFavorite
from .permissions import IsAdminUserRole, IsSuperAdmin
from .serializers import (
    AdminUserSerializer, FavoriteSerializer, RegisterSerializer, TokenWithUserSerializer, UserSerializer,
)

User = get_user_model()


class LoginView(TokenObtainPairView):
    serializer_class = TokenWithUserSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserAdminViewSet(viewsets.ModelViewSet):
    """Super Admins manage all users. Tournament Admins may list scorers (to assign them)."""

    serializer_class = AdminUserSerializer
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "email", "display_name"]
    ordering_fields = ["username", "date_joined"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAdminUserRole()]
        return [IsSuperAdmin()]

    def get_queryset(self):
        qs = User.objects.all().order_by("username")
        if not self.request.user.is_super_admin:
            qs = qs.filter(role=User.Role.SCORER, is_active=True)
        return qs

    def perform_create(self, serializer):
        user = serializer.save()
        audit(self.request.user, "user.create", user, role=user.role)

    def perform_update(self, serializer):
        user = serializer.save()
        audit(self.request.user, "user.update", user, role=user.role, is_active=user.is_active)

    def perform_destroy(self, instance):
        # Deactivate instead of deleting so scoring history stays attributable.
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        audit(self.request.user, "user.deactivate", instance)


class FavoriteViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return UserFavorite.objects.filter(user=self.request.user).select_related("team", "tournament", "match")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
