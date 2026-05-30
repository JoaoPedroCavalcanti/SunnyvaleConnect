"""Type/shape-only serializers for BBQ reservations."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from bbq_reservations.models import BBQReservationModel


class BBQReservationInputSerializer(serializers.Serializer):
    reservation_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True
    )
    reservation_date = serializers.DateField(required=True)
    guest_count = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class BBQReservationPatchSerializer(serializers.Serializer):
    reservation_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True
    )
    reservation_date = serializers.DateField(required=False)
    guest_count = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class BBQReservationOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = BBQReservationModel
        fields = ["id", "reservation_user", "reservation_date", "guest_count"]
