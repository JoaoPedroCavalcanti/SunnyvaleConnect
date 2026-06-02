"""Type/shape-only serializers for visitor access."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from visitor_access.models import (
    VisitorAccessModel,
    VisitorGroupMemberModel,
    VisitorGroupModel,
)


# ---------------------------------------------------------------------- #
# VisitorAccess                                                          #
# ---------------------------------------------------------------------- #
class VisitorAccessInputSerializer(serializers.Serializer):
    visitor_name = serializers.CharField(max_length=100, required=True)
    host_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True
    )
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    scheduled_date = serializers.DateTimeField(required=True)
    checkout_date_time = serializers.DateTimeField(required=False, allow_null=True)
    all_day = serializers.BooleanField(required=False, default=False)
    description = serializers.CharField(
        max_length=150, required=False, allow_blank=True, allow_null=True, default=""
    )


class VisitorAccessOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorAccessModel
        fields = "__all__"


# ---------------------------------------------------------------------- #
# VisitorGroup                                                           #
# ---------------------------------------------------------------------- #
class VisitorGroupMemberInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(
        required=False, allow_blank=True, allow_null=True, default=""
    )


class VisitorGroupMemberOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorGroupMemberModel
        fields = ["id", "name", "email", "created_at"]


class VisitorGroupInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=True)
    members = VisitorGroupMemberInputSerializer(many=True, required=False, default=list)


class VisitorGroupPatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    members = VisitorGroupMemberInputSerializer(many=True, required=False)


class VisitorGroupOutputSerializer(serializers.ModelSerializer):
    members = VisitorGroupMemberOutputSerializer(many=True, read_only=True)

    class Meta:
        model = VisitorGroupModel
        fields = [
            "id",
            "name",
            "host_user",
            "members",
            "created_at",
            "updated_at",
        ]


class VisitorGroupScheduleInputSerializer(serializers.Serializer):
    scheduled_date = serializers.DateTimeField(required=True)
    checkout_date_time = serializers.DateTimeField(required=False, allow_null=True)
    all_day = serializers.BooleanField(required=False, default=False)
    description = serializers.CharField(
        max_length=150, required=False, allow_blank=True, allow_null=True, default=""
    )
