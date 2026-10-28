"""Role-based access control used by every API view.

The frontend hides controls by role, but these checks are the real gate.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_super_admin(user):
    return bool(user and user.is_authenticated and user.is_super_admin)


def is_admin_user(user):
    """Super Admin or Tournament Admin."""
    return bool(user and user.is_authenticated and (user.is_super_admin or user.is_tournament_admin))


def can_manage_tournament(user, tournament):
    if not (user and user.is_authenticated):
        return False
    if user.is_super_admin:
        return True
    return user.is_tournament_admin and tournament.admins.filter(pk=user.pk).exists()


def can_manage_match(user, match):
    return can_manage_tournament(user, match.tournament)


def can_score_match(user, match):
    """Assigned scorers, the tournament's admins and Super Admins may score."""
    if not (user and user.is_authenticated):
        return False
    if can_manage_match(user, match):
        return True
    return match.scorer_assignments.filter(scorer=user, is_active=True).exists()


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_super_admin(request.user)


class IsAdminUserRole(BasePermission):
    """Super Admin or Tournament Admin."""

    def has_permission(self, request, view):
        return is_admin_user(request.user)


class ReadOnlyOrAdminRole(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_admin_user(request.user)
