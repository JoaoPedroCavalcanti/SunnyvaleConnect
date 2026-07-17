"""Plain APIViews for delivery notifications."""

from dataclasses import asdict

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from delivery_notification.serializers import (
    DeliveryApartmentListItemSerializer,
    DeliveryNotificationInputSerializer,
    DeliveryNotificationOutputSerializer,
    PaginatedDeliveryNotificationOutputSerializer,
)
from shared.container import container
from shared.permissions import IsAdminOrDoorman


@extend_schema(tags=["delivery_notification"])
class DeliveryApartmentListView(APIView):
    permission_classes = [IsAdminOrDoorman]

    @extend_schema(responses={200: DeliveryApartmentListItemSerializer(many=True)})
    def get(self, request):
        items = container.delivery_notification_service.list_apartments(request.user)
        payload = [asdict(item) for item in items]
        return Response(
            DeliveryApartmentListItemSerializer(payload, many=True).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["delivery_notification"])
class SendDeliveryNotificationView(APIView):
    permission_classes = [IsAdminOrDoorman]

    @extend_schema(
        request=DeliveryNotificationInputSerializer,
        responses={200: DeliveryNotificationOutputSerializer},
    )
    def post(self, request):
        serializer = DeliveryNotificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.delivery_notification_service.send(
            request.user, serializer.validated_data
        )
        return Response(
            DeliveryNotificationOutputSerializer(instance).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["delivery_notification"])
class ListDeliveryNotificationsView(APIView):
    permission_classes = [IsAdminOrDoorman]

    @extend_schema(
        responses={200: PaginatedDeliveryNotificationOutputSerializer}
    )
    def get(self, request):
        items = container.delivery_notification_service.list(request.user)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(items, request, view=self)
        serializer = DeliveryNotificationOutputSerializer(page, many=True)
        return paginator.get_paginated_response(
            serializer.data,
        )


@extend_schema(tags=["delivery_notification"])
class DetailDeliveryNotificationView(APIView):
    permission_classes = [IsAdminOrDoorman]

    @extend_schema(responses={200: DeliveryNotificationOutputSerializer})
    def get(self, request, pk: int):
        instance = container.delivery_notification_service.get(request.user, pk)
        return Response(
            DeliveryNotificationOutputSerializer(instance).data,
            status=status.HTTP_200_OK,
        )
