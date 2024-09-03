from django.db import models
from django.contrib.auth import get_user_model


class BBQReservationModel(models.Model):
    reservation_user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    reservation_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    guest_count = models.PositiveIntegerField(blank=True, null=True)
    