from django.contrib.auth import get_user_model
from django.db import models


class ServiceRequestModel(models.Model):
    """A ticket opened by a resident asking the building staff to do
    something (fix a leak, schedule extra cleaning, prune a tree, etc.).

    A request is always created as PENDING by the resident. Cleaning staff
    or an admin accepts (optional note) or declines (justification required).
    The note/justification is stored in ``admin_response`` for others to read.
    Once accepted, the handler may mark it COMPLETED.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"
        COMPLETED = "COMPLETED", "Completed"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class ServiceType(models.TextChoices):
        CLEANING = "CLEANING", "Extra cleaning"
        MAINTENANCE = "MAINTENANCE", "General maintenance"
        PLUMBING = "PLUMBING", "Plumbing"
        ELECTRICAL = "ELECTRICAL", "Electrical"
        SECURITY = "SECURITY", "Security"
        LANDSCAPING = "LANDSCAPING", "Landscaping"
        PEST_CONTROL = "PEST_CONTROL", "Pest control"
        OTHER = "OTHER", "Other"

    requester = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="service_requests",
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.OTHER,
    )
    location = models.CharField(max_length=150, blank=True, default="")
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.LOW
    )
    request_scheduled_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )

    # Filled when the admin responds (accept/decline) or completes.
    admin_response = models.TextField(blank=True, default="")
    responded_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responded_service_requests",
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
