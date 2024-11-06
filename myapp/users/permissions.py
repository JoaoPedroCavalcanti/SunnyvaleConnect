from rest_framework.permissions import BasePermission


class CanCreateUser(BasePermission):
    """
    Custom permission to only allow unauthenticated users or admins to create a user.
    """

    def has_permission(self, request, view):
        # Allow if the user is not authenticated or is an admin
        return not request.user.is_authenticated or request.user.is_staff
