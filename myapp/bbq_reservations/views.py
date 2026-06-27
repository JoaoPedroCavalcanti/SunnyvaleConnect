"""Plain APIViews for BBQ reservations."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bbq_reservations.serializers import (
    BBQReservationInputSerializer,
    BBQReservationOutputSerializer,
    BBQReservationPatchSerializer,
    BBQReservationRejectSerializer,
)
from shared.container import container


@extend_schema(tags=["bbq_reservations"])
class BBQReservationListCreateView(APIView):
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
        responses={200: BBQReservationOutputSerializer(many=True)},
    )
    def get(self, request):
        status_filter = request.query_params.get("status")
        queryset = container.bbq_service.list(status=status_filter)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = BBQReservationOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=BBQReservationInputSerializer,
        responses={201: BBQReservationOutputSerializer},
    )
    def post(self, request):
        serializer = BBQReservationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.bbq_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            BBQReservationOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["bbq_reservations"])
class BBQReservationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: BBQReservationOutputSerializer})
    def get(self, request, pk: int):
        instance = container.bbq_service.get(pk)
        return Response(BBQReservationOutputSerializer(instance).data)

    @extend_schema(
        request=BBQReservationPatchSerializer,
        responses={200: BBQReservationOutputSerializer},
    )
    def patch(self, request, pk: int):
        serializer = BBQReservationPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.bbq_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(BBQReservationOutputSerializer(instance).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int):
        container.bbq_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["bbq_reservations"])
class BBQReservationApproveView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        request=None, responses={200: BBQReservationOutputSerializer}
    )
    def post(self, request, pk: int):
        instance = container.bbq_service.approve(request.user, pk)
        return Response(BBQReservationOutputSerializer(instance).data)


@extend_schema(tags=["bbq_reservations"])
class BBQReservationRejectView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        request=BBQReservationRejectSerializer,
        responses={200: BBQReservationOutputSerializer},
    )
    def post(self, request, pk: int):
        serializer = BBQReservationRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.bbq_service.reject(
            request.user,
            pk,
            reason=serializer.validated_data["reason"],
        )
        return Response(BBQReservationOutputSerializer(instance).data)
