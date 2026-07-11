"""Role-based DRF permission classes.

These complement the stock ``IsAuthenticated`` / ``IsAdminUser`` (which
keys off ``user.is_staff``) by reading ``user.role`` and
``employee_types`` directly. The service layer keeps
``role==ADMIN <=> is_staff=True`` in sync, so ``IsAdminUser`` and
``IsAdmin`` are equivalent today; ``IsAdmin`` is the preferred entry point
for new admin-only code.
"""

from rest_framework.permissions import BasePermission

from shared.roles import can_doorman_ops, can_manage_service_requests
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


class IsAdminOrDoorman(BasePermission):
    def has_permission(self, request, view) -> bool:
        return can_doorman_ops(request.user)


class IsAdminOrCleaning(BasePermission):
    def has_permission(self, request, view) -> bool:
        return can_manage_service_requests(request.user)


class IsPlatformSuperuser(BasePermission):
    """Platform Django superuser only (not condo staff)."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_superuser", False)
        )
