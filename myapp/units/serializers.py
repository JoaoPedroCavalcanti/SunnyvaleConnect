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
    """Legacy flat public item (kept for OpenAPI nested unit fields)."""

    def to_representation(self, instance):
        unit = instance["unit"]
        data = UnitOutputSerializer(unit).data
        data["is_occupied"] = instance["is_occupied"]
        return data


class UnitCatalogItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kind = serializers.CharField()
    name = serializers.CharField(allow_blank=True)
    apartment = serializers.CharField(allow_blank=True)
    block = serializers.CharField(allow_blank=True)
    label = serializers.CharField(allow_blank=True)
    floor = serializers.CharField(allow_null=True, required=False)
    display_name = serializers.CharField()
    is_occupied = serializers.BooleanField()


class UnitCatalogFloorSerializer(serializers.Serializer):
    floor = serializers.CharField(allow_blank=True)
    units = UnitCatalogItemSerializer(many=True)


class UnitCatalogBlockSerializer(serializers.Serializer):
    block = serializers.CharField(allow_blank=True)
    floors = UnitCatalogFloorSerializer(many=True)


class UnitCatalogOutputSerializer(serializers.Serializer):
    condominium_id = serializers.IntegerField()
    condominium_code = serializers.CharField()
    layout = serializers.ChoiceField(choices=["blocks", "floors", "flat"])
    blocks = UnitCatalogBlockSerializer(many=True)
    floors = UnitCatalogFloorSerializer(many=True)
    units = UnitCatalogItemSerializer(many=True)
    named = UnitCatalogItemSerializer(many=True)


class UnitFilterOptionsFieldSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    options = serializers.ListField(child=serializers.CharField())


class UnitFloorFilterOptionsSerializer(UnitFilterOptionsFieldSerializer):
    options_by_block = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
    )


class UnitCatalogFiltersBagSerializer(serializers.Serializer):
    block = UnitFilterOptionsFieldSerializer()
    floor = UnitFloorFilterOptionsSerializer()
    apartment = UnitFilterOptionsFieldSerializer()
    name = UnitFilterOptionsFieldSerializer()


class UnitCatalogFiltersOutputSerializer(serializers.Serializer):
    condominium_id = serializers.IntegerField()
    condominium_code = serializers.CharField()
    layout = serializers.ChoiceField(choices=["blocks", "floors", "flat"])
    filters = UnitCatalogFiltersBagSerializer()


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


class UnitBulkBlockSerializer(serializers.Serializer):
    """Named tower/wing: APARTMENT_BLOCK units as ``{floor}{unit}`` + block."""

    block = serializers.CharField(required=True, max_length=50)
    floors = serializers.IntegerField(required=True, min_value=1, max_value=100)
    units = serializers.ListField(
        child=serializers.CharField(max_length=10),
        allow_empty=False,
        required=True,
    )


class UnitBulkTowerSerializer(serializers.Serializer):
    """Single building without block: APARTMENT units as ``{floor}{unit}``."""

    floors = serializers.IntegerField(required=True, min_value=1, max_value=100)
    units = serializers.ListField(
        child=serializers.CharField(max_length=10),
        allow_empty=False,
        required=True,
    )


class UnitBulkNumberRangeSerializer(serializers.Serializer):
    """Sequential numbers — houses or flat apt numbers without floors.

    ``pad=2`` → ``01``..``90``; ``pad=0`` → ``1``..``90``.
    """

    start = serializers.IntegerField(required=True, min_value=1)
    end = serializers.IntegerField(required=True, min_value=1)
    pad = serializers.IntegerField(required=False, min_value=0, max_value=6, default=0)
    as_named = serializers.BooleanField(
        required=False,
        default=False,
        help_text="If true, create NAMED units (Casa 1); else APARTMENT numbers.",
    )
    name_prefix = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=80,
        default="Casa ",
    )


class UnitBulkProvisionInputSerializer(serializers.Serializer):
    """Superuser-only recipe to generate many units at once.

    Floor grids build numbers as ``{floor}{unit}`` — e.g. floor 15 +
    ``"01"`` → ``"1501"``.
    """

    condominium_id = serializers.IntegerField(required=False)
    condominium_code = serializers.CharField(
        required=False, allow_blank=True, max_length=32
    )
    skip_existing = serializers.BooleanField(required=False, default=True)
    blocks = UnitBulkBlockSerializer(many=True, required=False, default=list)
    towers = UnitBulkTowerSerializer(many=True, required=False, default=list)
    number_range = UnitBulkNumberRangeSerializer(required=False, allow_null=True)
    apartments = serializers.ListField(
        child=serializers.CharField(max_length=10),
        required=False,
        default=list,
    )
    named_units = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )


class UnitBulkProvisionOutputSerializer(serializers.Serializer):
    condominium_id = serializers.IntegerField()
    condominium_code = serializers.CharField()
    created_count = serializers.IntegerField()
    skipped_count = serializers.IntegerField()
    created = UnitOutputSerializer(many=True)


class UnitRequestSerializer(serializers.Serializer):
    """Embedded in signup payloads to declare unit join intent."""

    unit_id = serializers.IntegerField(required=True)


class UnitMembershipRequestSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(required=True)
