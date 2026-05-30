from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from users.serializers import UserSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from users.permissions import CanCreateUser


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    http_method_names = ["get", "post", "delete", "patch"]
    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):
        User = get_user_model()

        if self.request.user.is_staff:
            return User.objects.all().order_by("id")

        return User.objects.filter(pk=self.request.user.pk).order_by("id")

    def get_permissions(self):
        if self.request.method == "POST":
            return [CanCreateUser()]
        return super().get_permissions()

    @action(methods=["get", "patch"], detail=False, url_path="me")
    def me(self, request):
        """Return (or update) the currently authenticated user without
        exposing their primary key in the URL."""
        if request.method == "PATCH":
            serializer = self.get_serializer(
                request.user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(self.get_serializer(request.user).data)
