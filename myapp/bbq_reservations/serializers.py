"""Type/shape-only serializers for BBQ reservations."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from bbq_reservations.models import BBQReservationModel


class BBQReservationInputSerializer(serializers.Serializer):
    """Input payload.

    ``reservation_user`` is optional. Regular users typically omit it;
    if they do send their own id, the service tolerates it. Only admins
    may pass a different user's id.
    """

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


class BBQReservationPatchSerializer(serializers.Serializer):
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


class BBQReservationOutputSerializer(serializers.ModelSerializer):
    """Output payload.

    ``household`` is exposed inline so the front can show "Booked by
    apt 1101/A" without an extra request. ``reservation_user`` keeps
    the snapshot of who created the entry (useful for the front to
    render the morador name).
    """

    household = serializers.SerializerMethodField()
    reservation_user = serializers.SerializerMethodField()

    class Meta:
        model = BBQReservationModel
        fields = [
            "id",
            "reservation_date",
            "start_time",
            "end_time",
            "guest_count",
            "status",
            "household",
            "reservation_user",
            "created_at",
        ]

    def get_household(self, obj) -> dict | None:
        if not obj.household_id:
            return None
        h = obj.household
        return {
            "id": h.id,
            "apartment": h.apartment,
            "block": h.block,
        }

    def get_reservation_user(self, obj) -> dict | None:
        if not obj.reservation_user_id:
            return None
        u = obj.reservation_user
        return {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
        }
