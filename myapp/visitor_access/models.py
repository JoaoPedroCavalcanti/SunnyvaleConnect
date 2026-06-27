from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


class VisitorGroupModel(models.Model):
    """Reusable group of visitors (e.g. 'Família Pai')."""

    name = models.CharField(max_length=100)
    host_user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="visitor_groups"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("host_user", "name")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.host_user_id})"


class VisitorGroupMemberModel(models.Model):
    group = models.ForeignKey(
        VisitorGroupModel, on_delete=models.CASCADE, related_name="members"
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


class VisitorAccessModel(models.Model):
    class Status(models.TextChoices):
        # Persisted states (set by the service)
        SCHEDULED = "SCHEDULED", "Agendado"
        CHECKED_IN = "CHECKED_IN", "Check-in feito"
        CHECKED_OUT = "CHECKED_OUT", "Concluído"
        CANCELLED = "CANCELLED", "Cancelado"
        # Derived states (never persisted, surface via display_status):
        # the visit went past its window without progressing further.
        NO_SHOW = "NO_SHOW", "Não compareceu"
        EXPIRED = "EXPIRED", "Expirado sem checkout"

    # Statuses that the database is allowed to hold.
    PERSISTED_STATUSES = frozenset(
        {Status.SCHEDULED, Status.CHECKED_IN, Status.CHECKED_OUT, Status.CANCELLED}
    )

    visitor_name = models.CharField(max_length=100)
    host_user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, blank=True, null=True, default=None
    )
    visitor_group = models.ForeignKey(
        VisitorGroupModel,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        related_name="visits",
    )
    email = models.EmailField(blank=True, null=True, default="")
    scheduled_date = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    checkin_date_time = models.DateTimeField(blank=True, null=True)
    checkout_date_time = models.DateTimeField(blank=True, null=True)
    checkin_code = models.CharField(max_length=10)
    checkout_code = models.CharField(max_length=10)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(max_length=150, blank=True, null=True, default="")
    qr_access_enabled = models.BooleanField(default=False)
    access_token = models.CharField(
        max_length=64, blank=True, null=True, default=None, unique=True
    )
    access_code = models.CharField(
        max_length=10, blank=True, null=True, default=None, unique=True
    )

    @property
    def display_status(self) -> str:
        """Status the API exposes — promotes SCHEDULED/CHECKED_IN to
        NO_SHOW/EXPIRED once the visit window has passed.

        Pure derivation from this row's own fields; safe to call from
        serializers without touching the DB.
        """
        now = timezone.now()
        if self.status == self.Status.SCHEDULED:
            window_end = self.checkout_date_time or self.scheduled_date
            if window_end < now:
                return self.Status.NO_SHOW
        if (
            self.status == self.Status.CHECKED_IN
            and self.checkout_date_time is not None
            and self.checkout_date_time < now
        ):
            return self.Status.EXPIRED
        return self.status
