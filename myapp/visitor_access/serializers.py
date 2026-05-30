"""Type/shape-only serializers for visitor access."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from visitor_access.models import VisitorAccessModel


class VisitorAccessInputSerializer(serializers.Serializer):
    visitor_name = serializers.CharField(max_length=100, required=True)
    host_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True
    )
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    scheduled_date = serializers.DateTimeField(required=True)
    checkout_date_time = serializers.DateTimeField(required=False, allow_null=True)
    description = serializers.CharField(
        max_length=150, required=False, allow_blank=True, allow_null=True, default=""
    )


class VisitorAccessOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorAccessModel
        fields = "__all__"
