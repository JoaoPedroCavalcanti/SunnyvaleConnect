"""Plain APIViews for Hall reservations."""

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hall_reservations.serializers import (
    HallReservationInputSerializer,
    HallReservationOutputSerializer,
    HallReservationPatchSerializer,
)
from shared.container import container


class HallReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = container.hall_service.list()
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = HallReservationOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

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


class HallReservationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        instance = container.hall_service.get(pk)
        return Response(HallReservationOutputSerializer(instance).data)

    def patch(self, request, pk: int):
        serializer = HallReservationPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.hall_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(HallReservationOutputSerializer(instance).data)

    def delete(self, request, pk: int):
        container.hall_service.delete(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
