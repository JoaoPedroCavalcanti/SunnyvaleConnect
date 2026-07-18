from django.conf import settings
from django.db import models


class NotificationModel(models.Model):
    class Type(models.TextChoices):
        RESERVATION_APPROVED = "RESERVATION_APPROVED", "Reservation approved"
        RESERVATION_REJECTED = "RESERVATION_REJECTED", "Reservation rejected"
        VISITOR_CHECKIN = "VISITOR_CHECKIN", "Visitor check-in"
        VISITOR_ARRIVAL = "VISITOR_ARRIVAL", "Visitor arrival"
        DELIVERY = "DELIVERY", "Delivery"
        UNIT_JOIN_REQUEST = "UNIT_JOIN_REQUEST", "Unit join request"
        UNIT_REQUEST_APPROVED = "UNIT_REQUEST_APPROVED", "Unit request approved"
        UNIT_REQUEST_REJECTED = "UNIT_REQUEST_REJECTED", "Unit request rejected"
        SERVICE_REQUEST_RESPONDED = (
            "SERVICE_REQUEST_RESPONDED",
            "Service request responded",
        )
        GENERIC = "GENERIC", "Generic"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    condominium = models.ForeignKey(
        "condominiums.Condominium",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=40, choices=Type.choices, default=Type.GENERIC)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default="")
    data = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"]),
            models.Index(fields=["recipient", "read_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} → {self.recipient_id} ({self.id})"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None
