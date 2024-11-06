from rest_framework.serializers import ModelSerializer
from bbq_reservations.models import BBQReservationModel
from datetime import date, timedelta
from rest_framework.validators import ValidationError


class BBQReservationSerializer(ModelSerializer):
    class Meta:
        model = BBQReservationModel
        fields = ["id", "reservation_user", "reservation_date", "guest_count"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "reservation_user": {"required": False},
            "reservation_date": {"required": True},
            "guest_count": {"required": False},
        }

    # Recieve user from view
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    # If the date is in the past => 'The date is invalid.'
    # If date already exists => 'The date is invalid.'
    def validate_reservation_date(self, value):
        if value < date.today():
            raise ValidationError("The date is invalid.")
        if BBQReservationModel.objects.filter(reservation_date=value):
            raise ValidationError("The Barbecue has already been booked.")
        return value

    # If not admin and date is < than 30 days => 'You can not book the barbecue with less than 30 days before your last bookment.'
    def validate(self, attrs):
        if not self.user.is_staff:
            if attrs.get("reservation_user"):
                raise ValidationError("You can not pass a reservation_user.")

            attrs["reservation_user"] = self.user

        if not attrs.get("reservation_user"):
            raise ValidationError("reservation_user can not be empty.")

        # Check if is admin user
        if self.user.is_staff:
            return super().validate(attrs)

        reservations_from_user = BBQReservationModel.objects.filter(
            reservation_user=attrs.get("reservation_user")
        )

        # Get the last date of an object from an User
        last_date = date(2000, 1, 1)
        for obj in reservations_from_user:
            if obj.reservation_date > last_date:
                last_date = obj.reservation_date

        # Using timedelta and comparing if date is less than 30 days
        thirty_days = timedelta(days=30)
        days_remaining = attrs.get("reservation_date") - last_date
        if days_remaining < thirty_days:
            raise ValidationError(
                "You can not book the barbecue with less than 30 days before your last bookment."
            )
        return super().validate(attrs)

    # def validate_reservation_user(self, value):
    #     if not self.user.is_staff:
    #         if value and value != self.user:
    #             raise ValidationError("You can only define this fiels as None or yours.")
    #     return value
