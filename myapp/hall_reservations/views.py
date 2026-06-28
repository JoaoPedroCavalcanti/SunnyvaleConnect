"""Plain APIViews for Hall reservations."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hall_reservations.serializers import (
    HallReservationInputSerializer,
    HallReservationOutputSerializer,
    HallReservationPatchSerializer,
    HallReservationRejectSerializer,
)
from shared.container import container


@extend_schema(tags=["hall_reservations"])
class HallReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                description=(
                    "Filter by booking status. Useful for the admin "
                    "dashboard to fetch only the pending queue."
                ),
                required=False,
                type=str,
                enum=["PENDING", "APPROVED", "REJECTED"],
            ),
        ],
        responses={200: HallReservationOutputSerializer(many=True)},
    )
    def get(self, request):
        status_filter = request.query_params.get("status")
        queryset = container.hall_service.list(request.user, status=status_filter)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = HallReservationOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=HallReservationInputSerializer,
        responses={201: HallReservationOutputSerializer},
    )
    def post(self, request):
        serializer = HallReservationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.hall_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            HallReservationOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["hall_reservations"])
class HallReservationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: HallReservationOutputSerializer})
    def get(self, request, pk: int):
        instance = container.hall_service.get(request.user, pk)
        return Response(HallReservationOutputSerializer(instance).data)

    @extend_schema(
        request=HallReservationPatchSerializer,
        responses={200: HallReservationOutputSerializer},
    )
    def patch(self, request, pk: int):
        serializer = HallReservationPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.hall_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(HallReservationOutputSerializer(instance).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int):
        container.hall_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["hall_reservations"])
class HallReservationApproveView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        request=None, responses={200: HallReservationOutputSerializer}
    )
    def post(self, request, pk: int):
        instance = container.hall_service.approve(request.user, pk)
        return Response(HallReservationOutputSerializer(instance).data)


@extend_schema(tags=["hall_reservations"])
class HallReservationRejectView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        request=HallReservationRejectSerializer,
        responses={200: HallReservationOutputSerializer},
    )
    def post(self, request, pk: int):
        serializer = HallReservationRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.hall_service.reject(
            request.user,
            pk,
            reason=serializer.validated_data["reason"],
        )
        return Response(HallReservationOutputSerializer(instance).data)
