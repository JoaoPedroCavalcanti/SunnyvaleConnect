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
    guest_count = serializers.IntegerField(
        min_value=0, required=False, allow_null=True
    )


class HallReservationOutputSerializer(serializers.ModelSerializer):
    """Output payload with the household (apartment) inlined."""

    household = serializers.SerializerMethodField()
    reservation_user = serializers.SerializerMethodField()

    class Meta:
        model = HallReservationModel
        fields = [
            "id",
            "reservation_date",
            "guest_count",
            "household",
            "reservation_user",
            "created_at",
        ]

    def get_household(self, obj) -> dict | None:
        if not obj.household_id:
            return None
        h = obj.household
        return {"id": h.id, "apartment": h.apartment, "block": h.block}

    def get_reservation_user(self, obj) -> dict | None:
        if not obj.reservation_user_id:
            return None
        u = obj.reservation_user
        return {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
        }
