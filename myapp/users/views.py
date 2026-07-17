"""Plain APIViews for users."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from condominiums.serializers import CondominiumLookupOutputSerializer
from shared.container import container
from users.models import EmployeeType, UserRole
from users.serializers import (
    LoginInputSerializer,
    LoginOutputSerializer,
    PaginatedUserOutputSerializer,
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


def _parse_optional_bool(raw: str | None) -> bool | None:
    if raw is None or raw == "":
        return None
    normalized = raw.strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"Invalid boolean query value: {raw!r}.")


@extend_schema(tags=["users"])
class UserListCreateView(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="List users",
        description=(
            "Admins receive active accounts by default (residents, admins, "
            "employees). Pending / inactive users are excluded unless "
            "`is_active=false` is passed. "
            "Other callers only see themselves. "
            "Omit `role` to list all roles; use `role=RESIDENT`, `ADMIN` or "
            "`EMPLOYEE` to filter. "
            "Combine with `is_active` and `employee_type` when needed."
        ),
        parameters=[
            OpenApiParameter(
                name="role",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[c for c, _ in UserRole.choices],
                description="Filter by role (admin only). Omit to list all users.",
            ),
            OpenApiParameter(
                name="is_active",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filter by active status (admin only). "
                    "Defaults to true when omitted."
                ),
            ),
            OpenApiParameter(
                name="employee_type",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[c for c, _ in EmployeeType.choices],
                description=(
                    "Filter employees by subtype (admin only). "
                    "Use with or without `role=EMPLOYEE`."
                ),
            ),
        ],
        responses={200: PaginatedUserOutputSerializer},
    )
    def get(self, request):
        role = request.query_params.get("role") or None
        try:
            is_active = _parse_optional_bool(request.query_params.get("is_active"))
        except ValueError as exc:
            raise ValidationError({"is_active": str(exc)}) from exc
        employee_type = request.query_params.get("employee_type") or None
        queryset = container.user_service.list_for(
            request.user,
            role=role,
            is_active=is_active,
            employee_type=employee_type,
        )
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
        unit_request = data.pop("unit_request", None)
        user = container.unit_signup_service.signup(
            request.user, data, unit_request
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
        description=(
            "Condominium admins may edit any exposed field of a user in their "
            "condominium except password. Username and CPF remain immutable "
            "for self-service updates."
        ),
    )
    def patch(self, request, pk: int):
        serializer = UserPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = container.user_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(UserOutputSerializer(user).data)

    @extend_schema(
        responses={204: None},
        description=(
            "Admin-only soft deletion. Deactivates the account, closes its "
            "active unit memberships and transfers ownership to the oldest "
            "active member when available. Admins cannot deactivate themselves."
        ),
    )
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
            serializer.validated_data["email"],
            serializer.validated_data["password"],
        )
        kind = result["kind"]
        condominium_payload = None
        if result.get("condominium") is not None:
            condominium_payload = CondominiumLookupOutputSerializer(
                result["condominium"], context={"request": request}
            ).data

        if kind == KIND_OK:
            user = result["user"]
            refresh = RefreshToken.for_user(user)
            refresh["role"] = user.role
            refresh["employee_types"] = list(getattr(user, "employee_types", None) or [])
            refresh["condominium_id"] = user.condominium_id
            access = refresh.access_token
            access["role"] = user.role
            access["employee_types"] = list(
                getattr(user, "employee_types", None) or []
            )
            access["condominium_id"] = user.condominium_id
            return Response(
                {
                    "access": str(access),
                    "refresh": str(refresh),
                    "condominium": condominium_payload,
                }
            )

        if kind == KIND_PENDING:
            return Response(
                {
                    "detail": "Your account is waiting for approval.",
                    "code": KIND_PENDING,
                    "unit": result["unit"],
                    "condominium": condominium_payload,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if kind == KIND_DISABLED:
            return Response(
                {
                    "detail": "Your account is disabled. Contact the administrator.",
                    "code": KIND_DISABLED,
                    "condominium": condominium_payload,
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
        payload = UserOutputSerializer(request.user).data
        if request.user.condominium_id:
            payload["condominium"] = CondominiumLookupOutputSerializer(
                request.user.condominium, context={"request": request}
            ).data
        return Response(payload)

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
