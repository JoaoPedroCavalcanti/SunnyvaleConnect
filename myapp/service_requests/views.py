"""Plain APIViews for service requests."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from service_requests.models import ServiceRequestModel
from service_requests.serializers import (
    ServiceRequestInputSerializer,
    ServiceRequestOutputSerializer,
    ServiceRequestPatchSerializer,
    ServiceRequestRespondSerializer,
)
from shared.container import container


def _enum_values(enum_cls) -> list[str]:
    return [c.value for c in enum_cls]


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
                    "Filter by status. Residents only see their own "
                    "requests; admins see every request."
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
        ],
        responses={200: ServiceRequestOutputSerializer(many=True)},
    )
    def get(self, request):
        queryset = container.service_request_service.list(
            request.user,
            status=request.query_params.get("status"),
            priority=request.query_params.get("priority"),
            service_type=request.query_params.get("service_type"),
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
    """Admin-only endpoint to accept or decline a pending request.

    The request body always carries a non-empty ``response`` field — the
    motivation that the resident will see.
    """

    permission_classes = [IsAdminUser]

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

    permission_classes = [IsAdminUser]

    @extend_schema(
        request=None, responses={200: ServiceRequestOutputSerializer}
    )
    def post(self, request, pk: int):
        instance = container.service_request_service.complete(request.user, pk)
        return Response(ServiceRequestOutputSerializer(instance).data)
