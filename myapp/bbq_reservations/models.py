from django.contrib.auth import get_user_model
from django.db import models


class BBQReservationModel(models.Model):
    """A booking for the shared barbecue area.

    The booking belongs to a ``unit`` (the apartment); ownership is
    scoped per apartment, not per user. ``reservation_user`` keeps a
    pointer to the person who actually created the entry (informational,
    for the front to render "booked by X").

    ``status`` drives the approval workflow. Bookings created by a
    regular morador are PENDING until an admin approves them; bookings
    created directly by an admin are auto-APPROVED. Only APPROVED
    bookings consume the time slot (no overlap; min 30-minute gap).
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
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
