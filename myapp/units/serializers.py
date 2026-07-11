"""Type/shape-only serializers for units app."""

from rest_framework import serializers

from units.models import Unit, UnitMembership


class UnitCreateInputSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Unit.Kind.choices, required=True)
    name = serializers.CharField(
        required=False, allow_blank=True, max_length=100, default=""
    )
    apartment = serializers.CharField(
        required=False, allow_blank=True, max_length=10, default=""
    )
    block = serializers.CharField(
        required=False, allow_blank=True, max_length=10, default=""
    )


class UnitOutputSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = [
            "id",
            "kind",
            "name",
            "apartment",
            "block",
            "status",
            "display_name",
            "created_at",
        ]

    def get_display_name(self, obj) -> str:
        return obj.display_name()


class UnitPublicOutputSerializer(serializers.Serializer):
    """Public list item: unit fields plus ``is_occupied``."""

    def to_representation(self, instance):
        unit = instance["unit"]
        data = UnitOutputSerializer(unit).data
        data["is_occupied"] = instance["is_occupied"]
        return data


class UnitWithMembersOutputSerializer(serializers.Serializer):
    def to_representation(self, instance):
        unit = instance["unit"]
        members = instance.get("members") or []
        data = UnitOutputSerializer(unit).data
        data["members"] = UnitMembershipOutputSerializer(members, many=True).data
        return data


class UnitMembershipUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    cpf = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)


class UnitMembershipOutputSerializer(serializers.ModelSerializer):
    user = UnitMembershipUserSerializer(read_only=True)

    class Meta:
        model = UnitMembership
        fields = [
            "id",
            "unit",
            "user",
            "role",
            "status",
            "joined_at",
            "left_at",
        ]


class PendingUnitApprovalSerializer(serializers.ModelSerializer):
    user = UnitMembershipUserSerializer(read_only=True)
    unit = UnitOutputSerializer(read_only=True)

    class Meta:
        model = UnitMembership
        fields = [
            "id",
            "unit",
            "user",
            "role",
            "status",
            "joined_at",
        ]


class UnitMembershipRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class UnitRequestSerializer(serializers.Serializer):
    """Embedded in signup payloads to declare unit join intent."""

    unit_id = serializers.IntegerField(required=True)


class UnitMembershipRequestSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(required=True)
