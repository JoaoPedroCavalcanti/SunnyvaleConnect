from django.contrib.auth import get_user_model
from django.db import models


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
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(max_length=150, blank=True, null=True, default="")
    link_checkin = models.CharField(max_length=255, blank=True, null=True)
    link_checkout = models.CharField(max_length=255, blank=True, null=True)
