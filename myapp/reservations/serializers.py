from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from reservations.models import ReservableLocation, Reservation


class TenantTargetSerializer(serializers.Serializer):
    condominium_id = serializers.IntegerField(required=False)
    condominium_code = serializers.CharField(
        required=False, allow_blank=False, max_length=8
    )


class ReservableLocationInputSerializer(serializers.Serializer):
    condominium_id = serializers.IntegerField(required=False)
    condominium_code = serializers.CharField(
        required=False, allow_blank=False, max_length=8
    )
    name = serializers.CharField(required=True, max_length=150)
    description = serializers.CharField(
        required=False, allow_blank=True
    )
    icon = serializers.CharField(
        required=False, allow_blank=True, max_length=100
    )


class ReservableLocationPatchSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=150)
    description = serializers.CharField(
        required=False, allow_blank=True
    )
    icon = serializers.CharField(
        required=False, allow_blank=True, max_length=100
    )


class ReservableLocationOutputSerializer(serializers.ModelSerializer):
    condominium_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ReservableLocation
        fields = [
            "id",
            "condominium_id",
            "name",
            "description",
            "icon",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ReservationInputSerializer(serializers.Serializer):
    location_id = serializers.IntegerField(required=True)
    reservation_user_id = serializers.IntegerField(
        required=False, allow_null=True
    )
    reservation_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    guest_count = serializers.IntegerField(
        required=False, allow_null=True, min_value=0
    )


class ReservationPatchSerializer(serializers.Serializer):
    location_id = serializers.IntegerField(required=False)
    reservation_user_id = serializers.IntegerField(
        required=False, allow_null=True
    )
    reservation_date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    guest_count = serializers.IntegerField(
        required=False, allow_null=True, min_value=0
    )


class ReservationRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False)


class AvailabilityQuerySerializer(serializers.Serializer):
    from_date = serializers.DateField(required=True)
    to_date = serializers.DateField(required=True)


class AvailabilityBookingSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    start_time = serializers.TimeField(allow_null=True)
    end_time = serializers.TimeField(allow_null=True)
    status = serializers.CharField()
    unit = serializers.DictField(allow_null=True)
    reservation_user = serializers.DictField(allow_null=True)


class FreeSlotSerializer(serializers.Serializer):
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()


class DayAvailabilitySerializer(serializers.Serializer):
    date = serializers.DateField()
    status = serializers.ChoiceField(
        choices=["free", "partial", "full", "past"]
    )
    bookings = AvailabilityBookingSerializer(many=True)
    free_slots = FreeSlotSerializer(many=True)


class AvailabilityRangeSerializer(serializers.Serializer):
    min_gap_minutes = serializers.IntegerField()
    days = DayAvailabilitySerializer(many=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["from"] = serializers.DateField(source="from_date")
        self.fields["to"] = serializers.DateField(source="to_date")


class ReservationUnitOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_name = serializers.CharField()


class ReservationUserOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()


class ReservationOutputSerializer(serializers.ModelSerializer):
    condominium_id = serializers.IntegerField(read_only=True)
    location = ReservableLocationOutputSerializer(read_only=True)
    unit = serializers.SerializerMethodField()
    reservation_user = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "id",
            "condominium_id",
            "location",
            "reservation_date",
            "start_time",
            "end_time",
            "guest_count",
            "status",
            "unit",
            "reservation_user",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(
        ReservationUnitOutputSerializer(allow_null=True)
    )
    def get_unit(self, obj):
        if not obj.unit_id:
            return None
        return {
            "id": obj.unit.id,
            "display_name": obj.unit.display_name(),
        }

    @extend_schema_field(
        ReservationUserOutputSerializer(allow_null=True)
    )
    def get_reservation_user(self, obj):
        if not obj.reservation_user_id:
            return None
        return {
            "id": obj.reservation_user.id,
            "username": obj.reservation_user.username,
            "full_name": obj.reservation_user.full_name,
        }


class PaginatedReservationOutputSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ReservationOutputSerializer(many=True)
