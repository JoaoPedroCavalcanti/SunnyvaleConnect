"""Type/shape-only serializers for delivery notifications."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from delivery_notification.models import DeliveryNotificationModel


class DeliveryNotificationInputSerializer(serializers.Serializer):
    user_to_delivery = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=True
    )
    title = serializers.CharField(max_length=100, required=True)
    description = serializers.CharField(
        max_length=300, required=False, allow_blank=True, default=""
    )
    delivery_platform = serializers.ChoiceField(
        choices=DeliveryNotificationModel.PLATFORMS, required=False, default="other"
    )
    delivery_from = serializers.CharField(max_length=150, required=True)
    delivery_to = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    priority_level = serializers.ChoiceField(
        choices=DeliveryNotificationModel.PRIORITY, required=False, default="low"
    )


class DeliveryNotificationOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryNotificationModel
        fields = "__all__"
