from rest_framework.serializers import ModelSerializer
from delivery_notification.models import DeliveryNotificationModel


class DeliveryNotificationSerializer(ModelSerializer):
    class Meta:
        model = DeliveryNotificationModel
        fields = "__all__"
        extra_kwargs = {
            "title": {"required": True},
            "delivery_from": {"required": True},
        }
