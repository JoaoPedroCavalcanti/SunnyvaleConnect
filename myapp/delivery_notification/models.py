from django.db import models

from households.models import Household


class DeliveryNotificationModel(models.Model):
    PLATFORMS = [
        ("ifood", "iFood"),
        ("rappi", "Rappi"),
        ("amazon", "Amazon"),
        ("mercado_livre", "Mercado Livre"),
        ("magalu", "Magalu"),
        ("shopee", "Shopee"),
        ("correios", "Correios"),
        ("other", "Outro"),
    ]
    PRIORITY = [("low", "Low"), ("medium", "Medium"), ("high", "High")]

    household = models.ForeignKey(Household, on_delete=models.CASCADE)
    notified_holder_name = models.CharField(max_length=150, blank=True, default="")
    notified_holder_email = models.EmailField(blank=True, default="")
    title = models.CharField(max_length=100, blank=True, null=True, default="")
    description = models.CharField(max_length=300, blank=True, null=True, default="")
    delivery_platform = models.CharField(
        choices=PLATFORMS, default="other", max_length=20
    )
    delivery_from = models.CharField(max_length=150, blank=True, null=True, default="")
    delivery_to = models.CharField(max_length=150, blank=True, null=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    priority_level = models.CharField(choices=PRIORITY, default="Low", max_length=50)
