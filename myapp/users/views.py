"""Plain APIViews for users."""

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.container import container
from users.serializers import (
    UserInputSerializer,
    UserOutputSerializer,
    UserPatchSerializer,
)


class UserListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        queryset = container.user_service.list_for(request.user)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(list(queryset), request, view=self)
        serializer = UserOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = UserInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = container.user_service.create(request.user, serializer.validated_data)
        return Response(UserOutputSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        user = container.user_service.get_for(request.user, pk)
        return Response(UserOutputSerializer(user).data)

    def patch(self, request, pk: int):
        serializer = UserPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = container.user_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(UserOutputSerializer(user).data)

    def delete(self, request, pk: int):
        container.user_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserOutputSerializer(request.user).data)

    def patch(self, request):
        serializer = UserPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = container.user_service.update_self(
            request.user, serializer.validated_data
        )
        return Response(UserOutputSerializer(user).data)
