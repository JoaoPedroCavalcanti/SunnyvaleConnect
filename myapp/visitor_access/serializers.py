"""Type/shape-only serializers for visitor access."""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from visitor_access.models import (
    VisitorAccessModel,
    VisitorGroupMemberModel,
    VisitorGroupModel,
)


# ---------------------------------------------------------------------- #
# VisitorGroup members (used both by VisitorGroup* and VisitorAccess*)   #
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
    # ``status`` exposes the *derived* state — NO_SHOW / EXPIRED show up
    # automatically once the visit window has passed, even though the
    # underlying row still says SCHEDULED / CHECKED_IN.
    status = serializers.CharField(source="display_status", read_only=True)
    # Group visits flag + their members embedded on the row, so the
    # front-end can render "group A scheduled for X" in a single card
    # without an extra request.
    is_group = serializers.SerializerMethodField()
    group_members = serializers.SerializerMethodField()

    class Meta:
        model = VisitorAccessModel
        fields = "__all__"

    def get_is_group(self, obj) -> bool:
        return obj.visitor_group_id is not None

    @extend_schema_field(VisitorGroupMemberOutputSerializer(many=True))
    def get_group_members(self, obj):
        if obj.visitor_group_id is None or obj.visitor_group is None:
            return []
        members = obj.visitor_group.members.all()
        return VisitorGroupMemberOutputSerializer(members, many=True).data


# ---------------------------------------------------------------------- #
# VisitorGroup (template)                                                #
# ---------------------------------------------------------------------- #
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
