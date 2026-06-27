"""Plain APIViews for visitor access."""

from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
)
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.container import container
from shared.permissions import IsAdminOrDoorman
from visitor_access.models import VisitorAccessModel
from visitor_access.serializers import (
    VisitorAccessInputSerializer,
    VisitorAccessOutputSerializer,
    VisitorAccessValidateInputSerializer,
    VisitorGroupInputSerializer,
    VisitorGroupOutputSerializer,
    VisitorGroupPatchSerializer,
    VisitorGroupScheduleInputSerializer,
)


_STATUS_PARAM = OpenApiParameter(
    name="status",
    required=False,
    type=str,
    enum=[c.value for c in VisitorAccessModel.Status],
    description=(
        "Filter by visit status. NO_SHOW and EXPIRED are "
        "derived from the persisted SCHEDULED/CHECKED_IN "
        "rows whose window has already elapsed."
    ),
)
_PERIOD_PARAM = OpenApiParameter(
    name="period",
    required=False,
    type=str,
    enum=["future", "past"],
    description=(
        "Filter by scheduled_date relative to now. "
        "'future' returns visits with scheduled_date >= now; "
        "'past' returns visits with scheduled_date < now."
    ),
)


@extend_schema(tags=["visitor_access"])
class VisitorAccessListCreateView(APIView):
    """Solo visitors only (group visits live under /groups/visits/)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[_PERIOD_PARAM, _STATUS_PARAM],
        responses={200: VisitorAccessOutputSerializer(many=True)},
    )
    def get(self, request):
        queryset = container.visitor_access_service.list_for(
            request.user,
            period=request.query_params.get("period"),
            status=request.query_params.get("status"),
            is_group=False,
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VisitorAccessOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=VisitorAccessInputSerializer,
        responses={201: VisitorAccessOutputSerializer},
    )
    def post(self, request):
        serializer = VisitorAccessInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.visitor_access_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            VisitorAccessOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["visitor_access"])
class VisitorAccessDetailView(APIView):
    """Shared by solo and group visits (a group visit is a single row)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: VisitorAccessOutputSerializer})
    def get(self, request, pk: int):
        instance = container.visitor_access_service.get_for(request.user, pk)
        return Response(VisitorAccessOutputSerializer(instance).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int):
        container.visitor_access_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["visitor_access"])
class VisitorAccessNotifyArrivalView(APIView):
    """Doorman manually notifies the host that a visitor has arrived."""

    permission_classes = [IsAuthenticated, IsAdminOrDoorman]

    @extend_schema(
        request=None,
        responses={200: VisitorAccessOutputSerializer},
    )
    def post(self, request, pk: int):
        instance = container.visitor_access_service.notify_arrival(request.user, pk)
        return Response(VisitorAccessOutputSerializer(instance).data)


@extend_schema(tags=["visitor_access"])
class VisitorAccessValidateView(APIView):
    """Doorman validates a visitor QR code or manual access code."""

    permission_classes = [IsAuthenticated, IsAdminOrDoorman]

    @extend_schema(
        request=VisitorAccessValidateInputSerializer,
        responses={200: VisitorAccessOutputSerializer},
    )
    def post(self, request):
        serializer = VisitorAccessValidateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.visitor_access_service.validate_access(
            request.user, serializer.validated_data["credential"]
        )
        return Response(VisitorAccessOutputSerializer(instance).data)


# ---------------------------------------------------------------------- #
# Visitor groups (template) — CRUD                                       #
# ---------------------------------------------------------------------- #
@extend_schema(tags=["visitor_access"])
class VisitorGroupListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: VisitorGroupOutputSerializer(many=True)})
    def get(self, request):
        queryset = container.visitor_group_service.list_for(request.user)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VisitorGroupOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=VisitorGroupInputSerializer,
        responses={201: VisitorGroupOutputSerializer},
    )
    def post(self, request):
        serializer = VisitorGroupInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.visitor_group_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            VisitorGroupOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["visitor_access"])
class VisitorGroupDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: VisitorGroupOutputSerializer})
    def get(self, request, pk: int):
        instance = container.visitor_group_service.get_for(request.user, pk)
        return Response(VisitorGroupOutputSerializer(instance).data)

    @extend_schema(
        request=VisitorGroupPatchSerializer,
        responses={200: VisitorGroupOutputSerializer},
    )
    def patch(self, request, pk: int):
        serializer = VisitorGroupPatchSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = container.visitor_group_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(VisitorGroupOutputSerializer(instance).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int):
        container.visitor_group_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["visitor_access"])
class VisitorGroupScheduleView(APIView):
    """Schedule a single visit that represents the whole group."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=VisitorGroupScheduleInputSerializer,
        responses={201: VisitorAccessOutputSerializer(many=True)},
    )
    def post(self, request, pk: int):
        serializer = VisitorGroupScheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit = container.visitor_group_service.schedule_visit(
            request.user, pk, serializer.validated_data
        )
        return Response(
            VisitorAccessOutputSerializer(visit, many=True).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["visitor_access"])
class VisitorGroupVisitsListView(APIView):
    """List scheduled *group* visits (one row per scheduled group visit).

    Same status/period filters as the solo listing — but here every row
    represents a group, not a single visitor.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[_PERIOD_PARAM, _STATUS_PARAM],
        responses={200: VisitorAccessOutputSerializer(many=True)},
    )
    def get(self, request):
        queryset = container.visitor_access_service.list_for(
            request.user,
            period=request.query_params.get("period"),
            status=request.query_params.get("status"),
            is_group=True,
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VisitorAccessOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
