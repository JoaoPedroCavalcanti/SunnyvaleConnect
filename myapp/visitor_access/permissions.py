from rest_framework.permissions import BasePermission


class IsAuthenticatedOrCheckInAndCheckOut(BasePermission):
    def has_permission(self, request, view):
        if view.action in ["checkin", "checkout"]:
            return True
        return (
            request.user and request.user.is_authenticated
        )  # Checa se tem uma instancia do objeto user e se esta autenticado
