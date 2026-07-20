from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.functions import Lower


class ReservableLocation(models.Model):
    class Icon(models.TextChoices):
        OUTDOOR_GRILL = "outdoor_grill", "Barbecue"
        CELEBRATION = "celebration", "Party"
        SPORTS_COURT = "sports_court", "Sports court"
        SPORTS_FIELD = "sports_field", "Sports field"
        MEETING_ROOM = "meeting_room", "Meeting room"
        FITNESS_CENTER = "fitness_center", "Fitness center"

    condominium = models.ForeignKey(
        "condominiums.Condominium",
        on_delete=models.PROTECT,
        related_name="reservable_locations",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(
        max_length=100,
        choices=Icon.choices,
        blank=True,
        default="",
    )
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


class ReservationDecision(models.Model):
    """Immutable audit row for reservation approvals and rejections."""

    class Action(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decisions",
    )
    condominium = models.ForeignKey(
        "condominiums.Condominium",
        on_delete=models.PROTECT,
        related_name="reservation_decisions",
    )
    location = models.ForeignKey(
        ReservableLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    location_name = models.CharField(max_length=150, blank=True, default="")
    location_icon = models.CharField(max_length=100, blank=True, default="")

    reservation_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    unit = models.ForeignKey(
        "units.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    unit_display_name = models.CharField(max_length=160, blank=True, default="")

    target = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    target_username = models.CharField(max_length=150, blank=True, default="")
    target_full_name = models.CharField(max_length=150, blank=True, default="")
    target_email = models.EmailField(blank=True, default="")

    actor = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    actor_username = models.CharField(max_length=150, blank=True, default="")
    actor_full_name = models.CharField(max_length=150, blank=True, default="")
    actor_email = models.EmailField(blank=True, default="")
    actor_role = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Capacity used for the decision: ADMIN.",
    )

    action = models.CharField(max_length=20, choices=Action.choices)
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["condominium", "-created_at"]),
            models.Index(fields=["location", "-created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.action} reservation@{self.location_name} "
            f"by {self.actor_username or '?'}"
        )
