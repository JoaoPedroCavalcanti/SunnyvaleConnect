"""Plain APIViews for users."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from shared.container import container
from users.serializers import (
    LoginInputSerializer,
    LoginOutputSerializer,
    UserInputSerializer,
    UserOutputSerializer,
    UserPatchSerializer,
)
from users.services.auth_service import (
    KIND_DISABLED,
    KIND_INVALID,
    KIND_OK,
    KIND_PENDING,
)


@extend_schema(tags=["users"])
class UserListCreateView(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(responses={200: UserOutputSerializer(many=True)})
    def get(self, request):
        queryset = container.user_service.list_for(request.user)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(list(queryset), request, view=self)
        serializer = UserOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=UserInputSerializer,
        responses={201: UserOutputSerializer},
    )
    def post(self, request):
        serializer = UserInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        household_request = data.pop("household_request", None)
        user = container.signup_service.signup(
            request.user, data, household_request
        )
        return Response(UserOutputSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["users"])
class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(responses={200: UserOutputSerializer})
    def get(self, request, pk: int):
        user = container.user_service.get_for(request.user, pk)
        return Response(UserOutputSerializer(user).data)

    @extend_schema(
        request=UserPatchSerializer,
        responses={200: UserOutputSerializer},
    )
    def patch(self, request, pk: int):
        serializer = UserPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = container.user_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(UserOutputSerializer(user).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int):
        container.user_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["auth"])
class LoginView(APIView):
    """Custom token endpoint with explicit feedback for pending accounts.

    Replaces the stock SimpleJWT TokenObtainPairView so the front can
    differentiate 'wrong password' from 'waiting for approval'.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginInputSerializer,
        responses={200: LoginOutputSerializer},
    )
    def post(self, request):
        serializer = LoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = container.auth_service.authenticate(
            serializer.validated_data["username"],
            serializer.validated_data["password"],
        )
        kind = result["kind"]

        if kind == KIND_OK:
            refresh = RefreshToken.for_user(result["user"])
            return Response(
                {"access": str(refresh.access_token), "refresh": str(refresh)}
            )

        if kind == KIND_PENDING:
            return Response(
                {
                    "detail": "Your account is waiting for approval.",
                    "code": KIND_PENDING,
                    "household": result["household"],
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if kind == KIND_DISABLED:
            return Response(
                {
                    "detail": "Your account is disabled. Contact the administrator.",
                    "code": KIND_DISABLED,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {"detail": "Invalid credentials.", "code": KIND_INVALID},
            status=status.HTTP_401_UNAUTHORIZED,
        )


@extend_schema(tags=["users"])
class UserMeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(responses={200: UserOutputSerializer})
    def get(self, request):
        return Response(UserOutputSerializer(request.user).data)

    @extend_schema(
        request=UserPatchSerializer,
        responses={200: UserOutputSerializer},
    )
    def patch(self, request):
        serializer = UserPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = container.user_service.update_self(
            request.user, serializer.validated_data
        )
        return Response(UserOutputSerializer(user).data)
