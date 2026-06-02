"""Role-based DRF permission classes.

These complement the stock ``IsAuthenticated`` / ``IsAdminUser`` (which
keys off ``user.is_staff``) by reading ``user.role`` directly. The
service layer keeps ``role==ADMIN <=> is_staff=True`` in sync, so
``IsAdminUser`` and ``IsAdmin`` are equivalent today; ``IsAdmin`` is the
preferred entry point for new code, ``IsAdminOrEmployee`` is for
endpoints that should be reachable by either an admin or a condo
employee (e.g. front desk operations).
"""

from rest_framework.permissions import BasePermission

from users.models import UserRole


def _has_role(user, *roles: str) -> bool:
    return (
        bool(user)
        and getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) in roles
    )


class IsAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return _has_role(request.user, UserRole.ADMIN)


class IsEmployee(BasePermission):
    def has_permission(self, request, view) -> bool:
        return _has_role(request.user, UserRole.EMPLOYEE)


class IsAdminOrEmployee(BasePermission):
    def has_permission(self, request, view) -> bool:
        return _has_role(request.user, UserRole.ADMIN, UserRole.EMPLOYEE)
