from django.contrib.auth import get_user_model
from django.db import models


class HallReservationModel(models.Model):
    """A booking for the shared party hall.

    Same shape as ``BBQReservationModel``: ownership is per household
    (apartment), so the 30-day cool-down is enforced across all members
    of the same apartment. ``reservation_user`` keeps a snapshot of who
    created the entry (informational).
    """

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="hall_reservations",
    )
    reservation_user = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
    )
    reservation_date = models.DateField()
    guest_count = models.PositiveIntegerField(blank=True, null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
