from django.db import models
from django.contrib.auth import get_user_model


class CondoPaymentModel(models.Model):
    STATUS = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
    ]

    payer_user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    status = models.CharField(max_length=50, choices=STATUS, default="pending")
    description = models.CharField(max_length=350, blank=True, null=True, default="")
    payment_link = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
