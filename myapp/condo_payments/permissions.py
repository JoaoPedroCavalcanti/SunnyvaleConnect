from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrReadyOnlyForAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        if request.method in SAFE_METHODS and request.user.is_authenticated:
            return True
        return False