from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.functions import Lower


class ReservableLocation(models.Model):
    condominium = models.ForeignKey(
        "condominiums.Condominium",
        on_delete=models.PROTECT,
        related_name="reservable_locations",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "condominium",
                name="uniq_reservable_location_condo_name_ci",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    condominium = models.ForeignKey(
        "condominiums.Condominium",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    location = models.ForeignKey(
        ReservableLocation,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    unit = models.ForeignKey(
        "units.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )
    reservation_user = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )
    reservation_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    guest_count = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reservation_date", "start_time", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(guest_count__isnull=True)
                | models.Q(guest_count__gte=0),
                name="reservation_guest_count_positive",
            )
        ]
        indexes = [
            models.Index(fields=["condominium", "reservation_date"]),
            models.Index(fields=["location", "reservation_date"]),
            models.Index(fields=["condominium", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.location_id} on {self.reservation_date}"
