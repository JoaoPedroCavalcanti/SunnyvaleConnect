"""Type/shape-only serializers for Hall reservations."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from hall_reservations.models import HallReservationModel


class HallReservationInputSerializer(serializers.Serializer):
    reservation_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        required=False,
        allow_null=True,
    )
    reservation_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    guest_count = serializers.IntegerField(
        min_value=0, required=False, allow_null=True
    )


class HallReservationPatchSerializer(serializers.Serializer):
    reservation_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        required=False,
        allow_null=True,
    )
    reservation_date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    guest_count = serializers.IntegerField(
        min_value=0, required=False, allow_null=True
    )


class HallReservationRejectSerializer(serializers.Serializer):
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

    def to_representation(self, instance):
        return {
            "from": instance.from_date,
            "to": instance.to_date,
            "min_gap_minutes": instance.min_gap_minutes,
            "days": DayAvailabilitySerializer(instance.days, many=True).data,
        }


class HallReservationOutputSerializer(serializers.ModelSerializer):
    """Output payload with the unit (apartment) inlined."""

    unit = serializers.SerializerMethodField()
    reservation_user = serializers.SerializerMethodField()

    class Meta:
        model = HallReservationModel
        fields = [
            "id",
            "reservation_date",
            "start_time",
            "end_time",
            "guest_count",
            "status",
            "unit",
            "reservation_user",
            "created_at",
        ]

    def get_unit(self, obj) -> dict | None:
        if not obj.unit_id:
            return None
        u = obj.unit
        return {"id": u.id, "display_name": u.display_name()}

    def get_reservation_user(self, obj) -> dict | None:
        if not obj.reservation_user_id:
            return None
        u = obj.reservation_user
        return {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
        }
