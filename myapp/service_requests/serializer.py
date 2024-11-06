from rest_framework import serializers
from django.contrib.auth import get_user_model
from service_requests.models import ServiceRequestModel
from rest_framework.exceptions import ValidationError
from datetime import datetime


class ServiceRequestSerializer(serializers.Serializer):
    PRIORITY_LEVEL = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]
    STATUS = [
        ("requested", "Requested"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    id = serializers.IntegerField(read_only=True)
    requester_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all()
    )
    title = serializers.CharField(max_length=150)
    request_description = serializers.CharField(required=False, allow_blank=True)
    service_type = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default="Other"
    )
    location = serializers.CharField(max_length=150, required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=PRIORITY_LEVEL, default="low")
    request_scheduled_date = serializers.DateTimeField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    status = serializers.ChoiceField(choices=STATUS, default="requested")

    # Staff will fill these fields
    responsable_staff = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    scheduled_date = serializers.DateTimeField(required=False, allow_null=True)
    more_details = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )

    def create(self, validated_data):
        return ServiceRequestModel.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if not validated_data:
            raise ValidationError("Invalid JSON")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["id"] = instance.id
        return representation

    def validate_scheduled_date(self, value):
        if value is not None and not isinstance(value, datetime):
            raise ValidationError(
                "O valor deve estar no formato de data e hora correto."
            )
        return value
