from django.contrib.auth import get_user_model
from django.db import models


class HallReservationModel(models.Model):
    """A booking for the shared party hall.

    Same shape as ``BBQReservationModel``: ownership is per unit
    (apartment). ``reservation_user`` keeps a snapshot of who created
    the entry (informational). ``status`` drives the approval workflow
    (PENDING by default; only APPROVED bookings occupy the slot — no
    overlap and a minimum 30-minute gap between bookings).
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    unit = models.ForeignKey(
        "units.Unit",
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
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    guest_count = models.PositiveIntegerField(blank=True, null=True, default=None)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
