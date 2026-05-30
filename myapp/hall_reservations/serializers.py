"""Type/shape-only serializers for Hall reservations."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from hall_reservations.models import HallReservationModel


class HallReservationInputSerializer(serializers.Serializer):
    reservation_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True
    )
    reservation_date = serializers.DateField(required=True)
    guest_count = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class HallReservationPatchSerializer(serializers.Serializer):
    reservation_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True
    )
    reservation_date = serializers.DateField(required=False)
    guest_count = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class HallReservationOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = HallReservationModel
        fields = ["id", "reservation_user", "reservation_date", "guest_count"]
