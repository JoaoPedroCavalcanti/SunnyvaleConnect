from django.contrib.auth import get_user_model
from django.db import models


class BBQReservationModel(models.Model):
    """A booking for the shared barbecue area.

    The booking belongs to a ``household`` (the apartment) so the 30-day
    cool-down rule and the ownership are scoped per apartment, not per
    user. ``reservation_user`` keeps a pointer to the person who actually
    created the entry (informational, for the front to render "booked
    by X").
    """

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bbq_reservations",
    )
    reservation_user = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
    )
    reservation_date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    guest_count = models.PositiveIntegerField(blank=True, null=True)
