"""Plain APIViews for BBQ reservations."""

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bbq_reservations.serializers import (
    BBQReservationInputSerializer,
    BBQReservationOutputSerializer,
    BBQReservationPatchSerializer,
)
from shared.container import container


class BBQReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = container.bbq_service.list()
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = BBQReservationOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

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


class BBQReservationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        instance = container.bbq_service.get(pk)
        return Response(BBQReservationOutputSerializer(instance).data)

    def patch(self, request, pk: int):
        serializer = BBQReservationPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.bbq_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(BBQReservationOutputSerializer(instance).data)

    def delete(self, request, pk: int):
        container.bbq_service.delete(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
