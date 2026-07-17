"""Type/shape-only serializers for delivery notifications."""

from rest_framework import serializers

from delivery_notification.models import DeliveryNotificationModel
from units.models import Unit


class DeliveryApartmentListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    holder_name = serializers.CharField(read_only=True)
    status = serializers.ChoiceField(choices=Unit.Status.choices, read_only=True)


class NotifiedToOutputSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)


class DeliveryNotificationInputSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(required=True)
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
    display_name = serializers.CharField(source="unit.display_name", read_only=True)
    notified_to = NotifiedToOutputSerializer(read_only=True)

    class Meta:
        model = DeliveryNotificationModel
        fields = [
            "id",
            "unit",
            "display_name",
            "notified_to",
            "title",
            "description",
            "delivery_platform",
            "delivery_from",
            "delivery_to",
            "created_at",
            "priority_level",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["display_name"] = instance.unit.display_name()
        data["notified_to"] = {
            "name": instance.notified_holder_name,
            "email": instance.notified_holder_email,
        }
        return data


class PaginatedDeliveryNotificationOutputSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = DeliveryNotificationOutputSerializer(many=True)
