"""Plain APIViews for service requests."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from service_requests.models import ServiceRequestModel
from service_requests.serializers import (
    PaginatedServiceRequestOutputSerializer,
    ServiceRequestInputSerializer,
    ServiceRequestOutputSerializer,
    ServiceRequestPatchSerializer,
    ServiceRequestRespondSerializer,
)
from shared.container import container
from shared.permissions import IsAdminOrCleaning


def _enum_values(enum_cls) -> list[str]:
    return [c.value for c in enum_cls]


def _parse_optional_bool(raw: str | None) -> bool:
    if raw is None or raw == "":
        return False
    normalized = raw.strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"Valor booleano inválido na query: {raw!r}.")


@extend_schema(tags=["service_requests"])
class ServiceRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                required=False,
                type=str,
                enum=_enum_values(ServiceRequestModel.Status),
                description=(
                    "Filter by status. Every authenticated user sees all requests."
                ),
            ),
            OpenApiParameter(
                name="priority",
                required=False,
                type=str,
                enum=_enum_values(ServiceRequestModel.Priority),
            ),
            OpenApiParameter(
                name="service_type",
                required=False,
                type=str,
                enum=_enum_values(ServiceRequestModel.ServiceType),
            ),
            OpenApiParameter(
                name="period",
                required=False,
                type=str,
                enum=["future", "past"],
                description=(
                    "Filters by request_scheduled_date relative to now."
                ),
            ),
            OpenApiParameter(
                name="mine",
                required=False,
                type=bool,
                description=(
                    "When true, only requests created by the authenticated user."
                ),
            ),
            OpenApiParameter(
                name="responded_by_me",
                required=False,
                type=bool,
                description=(
                    "When true, only requests this cleaning employee (or admin) "
                    "accepted/declined (responded_by = caller)."
                ),
            ),
        ],
        responses={200: PaginatedServiceRequestOutputSerializer},
    )
    def get(self, request):
        try:
            mine = _parse_optional_bool(request.query_params.get("mine"))
            responded_by_me = _parse_optional_bool(
                request.query_params.get("responded_by_me")
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        queryset = container.service_request_service.list(
            request.user,
            status=request.query_params.get("status"),
            priority=request.query_params.get("priority"),
            service_type=request.query_params.get("service_type"),
            period=request.query_params.get("period"),
            mine=mine,
            responded_by_me=responded_by_me,
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ServiceRequestOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=ServiceRequestInputSerializer,
        responses={201: ServiceRequestOutputSerializer},
    )
    def post(self, request):
        serializer = ServiceRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.service_request_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            ServiceRequestOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["service_requests"])
class ServiceRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ServiceRequestOutputSerializer})
    def get(self, request, pk: int):
        instance = container.service_request_service.get(request.user, pk)
        return Response(ServiceRequestOutputSerializer(instance).data)

    @extend_schema(
        request=ServiceRequestPatchSerializer,
        responses={200: ServiceRequestOutputSerializer},
    )
    def patch(self, request, pk: int):
        serializer = ServiceRequestPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.service_request_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(ServiceRequestOutputSerializer(instance).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int):
        container.service_request_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["service_requests"])
class ServiceRequestRespondView(APIView):
    """Admin or cleaning staff accept (optional note) or decline a request."""

    permission_classes = [IsAuthenticated, IsAdminOrCleaning]

    @extend_schema(
        request=ServiceRequestRespondSerializer,
        responses={200: ServiceRequestOutputSerializer},
    )
    def post(self, request, pk: int):
        serializer = ServiceRequestRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.service_request_service.respond(
            request.user,
            pk,
            serializer.validated_data["action"],
            serializer.validated_data["response"],
        )
        return Response(ServiceRequestOutputSerializer(instance).data)


@extend_schema(tags=["service_requests"])
class ServiceRequestCompleteView(APIView):
    """Admin-only endpoint to mark an accepted request as completed."""

    permission_classes = [IsAuthenticated, IsAdminOrCleaning]

    @extend_schema(
        request=None, responses={200: ServiceRequestOutputSerializer}
    )
    def post(self, request, pk: int):
        instance = container.service_request_service.complete(request.user, pk)
        return Response(ServiceRequestOutputSerializer(instance).data)
