"""Type/shape-only serializers for visitor access."""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from visitor_access.models import (
    VisitorAccessModel,
    VisitorContactModel,
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


class VisitorAccessHostOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    apartment = serializers.CharField(read_only=True)
    block = serializers.CharField(read_only=True)


class VisitorAccessGroupSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


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
    qr_access_enabled = serializers.BooleanField(required=False, default=False)
    description = serializers.CharField(
        max_length=150, required=False, allow_blank=True, allow_null=True, default=""
    )

    def validate(self, attrs):
        if attrs.get("qr_access_enabled") and not (attrs.get("email") or "").strip():
            raise serializers.ValidationError(
                {"email": "O e-mail do visitante é obrigatório quando o acesso por QR está ativado."}
            )
        return attrs


class VisitorAccessPatchSerializer(serializers.Serializer):
    visitor_name = serializers.CharField(max_length=100, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    scheduled_date = serializers.DateTimeField(required=False)
    checkout_date_time = serializers.DateTimeField(
        required=False, allow_null=True
    )
    all_day = serializers.BooleanField(required=False)
    description = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class VisitorAccessOutputSerializer(serializers.ModelSerializer):
    # ``status`` exposes the *derived* state — NO_SHOW / EXPIRED show up
    # automatically once the visit window has passed, even though the
    # underlying row still says SCHEDULED / CHECKED_IN.
    status = serializers.CharField(source="display_status", read_only=True)
    # Group visits flag + their members embedded on the row, so the
    # front-end can render "group A scheduled for X" in a single card
    # without an extra request.
    host = serializers.SerializerMethodField()
    visitor_group = serializers.SerializerMethodField()
    is_group = serializers.SerializerMethodField()
    group_members = serializers.SerializerMethodField()

    class Meta:
        model = VisitorAccessModel
        exclude = ["access_token", "access_code", "host_user"]

    @extend_schema_field(VisitorAccessHostOutputSerializer)
    def get_host(self, obj):
        user = obj.host_user
        if not user:
            return None
        return {
            "id": user.id,
            "full_name": user.full_name or user.username,
            "apartment": user.apartment or "",
            "block": user.block or "",
        }

    @extend_schema_field(VisitorAccessGroupSummarySerializer)
    def get_visitor_group(self, obj):
        group = obj.visitor_group
        if not group:
            return None
        return {"id": group.id, "name": group.name}

    def get_is_group(self, obj) -> bool:
        return obj.visitor_group_id is not None

    @extend_schema_field(VisitorGroupMemberOutputSerializer(many=True))
    def get_group_members(self, obj):
        if obj.visitor_group_id is None or obj.visitor_group is None:
            return []
        members = obj.visitor_group.members.all()
        return VisitorGroupMemberOutputSerializer(members, many=True).data


class VisitorAccessValidateInputSerializer(serializers.Serializer):
    credential = serializers.CharField(max_length=255, required=True)


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


class PaginatedVisitorAccessOutputSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = VisitorAccessOutputSerializer(many=True)


class PaginatedVisitorGroupOutputSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = VisitorGroupOutputSerializer(many=True)


class VisitorGroupScheduleInputSerializer(serializers.Serializer):
    scheduled_date = serializers.DateTimeField(required=True)
    checkout_date_time = serializers.DateTimeField(required=False, allow_null=True)
    all_day = serializers.BooleanField(required=False, default=False)
    qr_access_enabled = serializers.BooleanField(required=False, default=False)
    description = serializers.CharField(
        max_length=150, required=False, allow_blank=True, allow_null=True, default=""
    )


# ---------------------------------------------------------------------- #
# VisitorContact (saved solo visitor)                                    #
# ---------------------------------------------------------------------- #
class VisitorContactInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(
        required=False, allow_blank=True, allow_null=True, default=""
    )


class VisitorContactPatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    email = serializers.EmailField(
        required=False, allow_blank=True, allow_null=True
    )


class VisitorContactOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorContactModel
        fields = [
            "id",
            "name",
            "email",
            "host_user",
            "created_at",
            "updated_at",
        ]


class PaginatedVisitorContactOutputSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = VisitorContactOutputSerializer(many=True)


class VisitorContactScheduleInputSerializer(serializers.Serializer):
    scheduled_date = serializers.DateTimeField(required=True)
    checkout_date_time = serializers.DateTimeField(required=False, allow_null=True)
    all_day = serializers.BooleanField(required=False, default=False)
    qr_access_enabled = serializers.BooleanField(required=False, default=False)
    description = serializers.CharField(
        max_length=150, required=False, allow_blank=True, allow_null=True, default=""
    )
