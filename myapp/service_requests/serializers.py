"""Type/shape-only serializers for service requests."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from service_requests.models import ServiceRequestModel


class ServiceRequestInputSerializer(serializers.Serializer):
    requester_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=True
    )
    title = serializers.CharField(max_length=150, required=True)
    request_description = serializers.CharField(required=False, allow_blank=True)
    service_type = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default="Other"
    )
    location = serializers.CharField(max_length=150, required=False, allow_blank=True)
    priority = serializers.ChoiceField(
        choices=ServiceRequestModel.PRIORITY_LEVEL, default="low", required=False
    )
    request_scheduled_date = serializers.DateTimeField(required=True)
    status = serializers.ChoiceField(
        choices=ServiceRequestModel.STATUS, default="requested", required=False
    )
    responsable_staff = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    scheduled_date = serializers.DateTimeField(required=False, allow_null=True)
    more_details = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )


class ServiceRequestPatchSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150, required=False)
    request_description = serializers.CharField(required=False, allow_blank=True)
    service_type = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    location = serializers.CharField(max_length=150, required=False, allow_blank=True)
    priority = serializers.ChoiceField(
        choices=ServiceRequestModel.PRIORITY_LEVEL, required=False
    )
    request_scheduled_date = serializers.DateTimeField(required=False)
    status = serializers.ChoiceField(
        choices=ServiceRequestModel.STATUS, required=False
    )
    responsable_staff = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    scheduled_date = serializers.DateTimeField(required=False, allow_null=True)
    more_details = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )


class ServiceRequestOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequestModel
        fields = "__all__"
