from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from delivery_notification.serializer import DeliveryNotificationSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from sunnyValeConnect.utils.delivery_notification import send_delivery_notification
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from delivery_notification.models import DeliveryNotificationModel


@api_view(http_method_names=["post"])
@permission_classes([IsAdminUser])
def send_notification(request):
    serializer = DeliveryNotificationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()

        UserModel = get_user_model()
        user_id = serializer.data.get("user_to_delivery")
        user = get_object_or_404(UserModel, id=user_id)

        user_email = user.email
        user_name = user.username
        delivery_plataform = request.data.get("delivery_platform")
        delivery_from = request.data.get("delivery_from")
        send_delivery_notification(
            user_email, user_name, delivery_plataform, delivery_from
        )

        return Response(serializer.data, status=status.HTTP_200_OK)
    raise ValidationError(serializer.errors, status.HTTP_400_BAD_REQUEST)


@api_view(http_method_names=["GET"])
@permission_classes([IsAdminUser])
def list_notifications(request):
    # Obtém todos os objetos do DeliveryNotificationModel
    objects = DeliveryNotificationModel.objects.all()

    # Serializa os objetos obtidos
    serializer = DeliveryNotificationSerializer(objects, many=True)

    # Retorna a resposta com os dados serializados
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(http_method_names=["GET"])
@permission_classes([IsAdminUser])
def detail_notification(request, pk):
    notification = get_object_or_404(DeliveryNotificationModel, pk=pk)
    serializer = DeliveryNotificationSerializer(instance=notification)

    return Response(serializer.data, status=status.HTTP_200_OK)
