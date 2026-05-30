"""Plain APIViews for delivery notifications."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from delivery_notification.serializers import (
    DeliveryNotificationInputSerializer,
    DeliveryNotificationOutputSerializer,
)
from shared.container import container


@extend_schema(tags=["delivery_notification"])
class SendDeliveryNotificationView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        request=DeliveryNotificationInputSerializer,
        responses={200: DeliveryNotificationOutputSerializer},
    )
    def post(self, request):
        serializer = DeliveryNotificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.delivery_notification_service.send(
            serializer.validated_data
        )
        return Response(
            DeliveryNotificationOutputSerializer(instance).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["delivery_notification"])
class ListDeliveryNotificationsView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: DeliveryNotificationOutputSerializer(many=True)})
    def get(self, request):
        items = container.delivery_notification_service.list()
        return Response(
            DeliveryNotificationOutputSerializer(items, many=True).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["delivery_notification"])
class DetailDeliveryNotificationView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: DeliveryNotificationOutputSerializer})
    def get(self, request, pk: int):
        instance = container.delivery_notification_service.get(pk)
        return Response(
            DeliveryNotificationOutputSerializer(instance).data,
            status=status.HTTP_200_OK,
        )
