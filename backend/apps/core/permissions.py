"""DRF permission classes for role-based access (docs/api.md, docs/requirements.md §2)."""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdmin(BasePermission):
    """ADMIN role (or Django superuser)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_role("ADMIN"))


class IsModeratorOrAdmin(BasePermission):
    """MODERATOR or ADMIN role (or Django superuser)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_any_role("MODERATOR", "ADMIN"))


class IsArtist(BasePermission):
    """Granted ARTIST role (approved seller)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_role("ARTIST"))


class IsReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
