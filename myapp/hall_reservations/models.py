from django.db import models
from django.contrib.auth import get_user_model

class HallReservationModel(models.Model):
    reservation_user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, blank=True, null=True, default=None)
    reservation_date = models.DateField()
    guest_count = models.PositiveIntegerField(blank=True, null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
