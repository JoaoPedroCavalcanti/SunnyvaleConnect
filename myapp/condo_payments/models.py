from django.db import models
from django.contrib.auth import get_user_model


class CondoPaymentModel(models.Model):
    payer_user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    status = models.CharField(max_length=50, default="pending")
    description = models.CharField(max_length=350, blank=True, null=True, default="")
    payment_link = models.CharField(max_length=150)
    payment_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
