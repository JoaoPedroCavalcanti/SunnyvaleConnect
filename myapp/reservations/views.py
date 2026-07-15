from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from reservations.serializers import (
    AvailabilityQuerySerializer,
    AvailabilityRangeSerializer,
    PaginatedReservationOutputSerializer,
    ReservableLocationInputSerializer,
    ReservableLocationOutputSerializer,
    ReservableLocationPatchSerializer,
    ReservationInputSerializer,
    ReservationOutputSerializer,
    ReservationPatchSerializer,
    ReservationRejectSerializer,
    TenantTargetSerializer,
)
from shared.container import container


TENANT_PARAMETERS = [
    OpenApiParameter(
        "condominium_id", int, required=False, location="query"
    ),
    OpenApiParameter(
        "condominium_code", str, required=False, location="query"
    ),
]


def _tenant_query(request):
    serializer = TenantTargetSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


@extend_schema(tags=["reservations"])
class ReservableLocationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=TENANT_PARAMETERS,
        responses={200: ReservableLocationOutputSerializer(many=True)},
    )
    def get(self, request):
        result = container.reservable_location_service.list(
            request.user, _tenant_query(request)
        )
        return Response(
            ReservableLocationOutputSerializer(result, many=True).data
        )

    @extend_schema(
        request=ReservableLocationInputSerializer,
        responses={201: ReservableLocationOutputSerializer},
    )
    def post(self, request):
        serializer = ReservableLocationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.reservable_location_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            ReservableLocationOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["reservations"])
class ReservableLocationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=TENANT_PARAMETERS,
        responses={200: ReservableLocationOutputSerializer},
    )
    def get(self, request, pk):
        instance = container.reservable_location_service.get(
            request.user, pk, _tenant_query(request)
        )
        return Response(ReservableLocationOutputSerializer(instance).data)

    @extend_schema(
        request=ReservableLocationPatchSerializer,
        responses={200: ReservableLocationOutputSerializer},
    )
    def patch(self, request, pk):
        serializer = ReservableLocationPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.reservable_location_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(ReservableLocationOutputSerializer(instance).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        container.reservable_location_service.archive(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["reservations"])
class LocationAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("from", str, required=True, location="query"),
            OpenApiParameter("to", str, required=True, location="query"),
        ],
        responses={200: AvailabilityRangeSerializer},
    )
    def get(self, request, pk):
        serializer = AvailabilityQuerySerializer(
            data={
                "from_date": request.query_params.get("from"),
                "to_date": request.query_params.get("to"),
            }
        )
        serializer.is_valid(raise_exception=True)
        result = container.reservation_service.availability(
            request.user,
            pk,
            from_date=serializer.validated_data["from_date"],
            to_date=serializer.validated_data["to_date"],
        )
        return Response(AvailabilityRangeSerializer(result).data)


@extend_schema(tags=["reservations"])
class ReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="reservations_list",
        parameters=[
            OpenApiParameter(
                "status",
                str,
                required=False,
                location="query",
                enum=["PENDING", "APPROVED", "REJECTED"],
            ),
            OpenApiParameter(
                "condominium_id", int, required=False, location="query"
            ),
            OpenApiParameter(
                "period",
                str,
                required=False,
                location="query",
                enum=["future", "past"],
            ),
        ],
        responses={200: PaginatedReservationOutputSerializer},
    )
    def get(self, request):
        condominium_id = request.query_params.get("condominium_id")
        if condominium_id is not None:
            tenant = TenantTargetSerializer(
                data={"condominium_id": condominium_id}
            )
            tenant.is_valid(raise_exception=True)
            condominium_id = tenant.validated_data["condominium_id"]
        result = container.reservation_service.list(
            request.user,
            status=request.query_params.get("status"),
            period=request.query_params.get("period"),
            condominium_id=condominium_id,
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(result, request, view=self)
        return paginator.get_paginated_response(
            ReservationOutputSerializer(page, many=True).data
        )

    @extend_schema(
        request=ReservationInputSerializer,
        responses={201: ReservationOutputSerializer},
    )
    def post(self, request):
        serializer = ReservationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.reservation_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            ReservationOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["reservations"])
class ReservationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ReservationOutputSerializer})
    def get(self, request, pk):
        instance = container.reservation_service.get(request.user, pk)
        return Response(ReservationOutputSerializer(instance).data)

    @extend_schema(
        request=ReservationPatchSerializer,
        responses={200: ReservationOutputSerializer},
    )
    def patch(self, request, pk):
        serializer = ReservationPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.reservation_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(ReservationOutputSerializer(instance).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        container.reservation_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["reservations"])
class ReservationApproveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: ReservationOutputSerializer}
    )
    def post(self, request, pk):
        instance = container.reservation_service.approve(request.user, pk)
        return Response(ReservationOutputSerializer(instance).data)


@extend_schema(tags=["reservations"])
class ReservationRejectView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ReservationRejectSerializer,
        responses={200: ReservationOutputSerializer},
    )
    def post(self, request, pk):
        serializer = ReservationRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.reservation_service.reject(
            request.user,
            pk,
            reason=serializer.validated_data["reason"],
        )
        return Response(ReservationOutputSerializer(instance).data)
