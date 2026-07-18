"""Type/shape-only serializers for notifications."""

from rest_framework import serializers

from notifications.models import NotificationModel


class NotificationOutputSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = NotificationModel
        fields = [
            "id",
            "type",
            "title",
            "body",
            "data",
            "is_read",
            "read_at",
            "created_at",
        ]


class PaginatedNotificationOutputSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = NotificationOutputSerializer(many=True)


class UnreadCountOutputSerializer(serializers.Serializer):
    count = serializers.IntegerField()


class MarkAllReadOutputSerializer(serializers.Serializer):
    updated = serializers.IntegerField()
