from django.db import models
from django.contrib.auth import get_user_model


class VisitorAccessModel(models.Model):
    visitor_name = models.CharField(max_length=100)
    host_user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, blank=True, null=True, default=None
    )
    email = models.EmailField(blank=True, null=True, default="")
    scheduled_date = models.DateTimeField()
    checkin_date_time = models.DateTimeField(blank=True, null=True)
    checkout_date_time = models.DateTimeField(blank=True, null=True)
    checkin_code = models.CharField(max_length=10)
    checkout_code = models.CharField(max_length=10)
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(max_length=150, blank=True, null=True, default="")
    link_checkin = models.CharField(max_length=50, blank=True, null=True)
    link_checkout = models.CharField(max_length=50, blank=True, null=True)
