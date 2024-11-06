from django.db import models
from django.contrib.auth import get_user_model


# Create your models here.
class DeliveryNotificationModel(models.Model):
    PLATFORMS = [
        ("ifood", "Ifood"),
        ("rappi", "Rappi"),
        ("uber eats", "Uber Eats"),
        ("doordash", "DoorDash"),
        ("just eat", "Just Eat"),
        ("other", "Other"),
    ]
    PRIORITY = [("low", "Low"), ("medium", "Medium"), ("high", "High")]

    user_to_delivery = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    title = models.CharField(max_length=100, blank=True, null=True, default="")
    description = models.CharField(max_length=300, blank=True, null=True, default="")
    delivery_platform = models.CharField(
        choices=PLATFORMS, default="Other", max_length=20
    )
    delivery_from = models.CharField(max_length=150, blank=True, null=True, default="")
    delivery_to = models.CharField(max_length=150, blank=True, null=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    priority_level = models.CharField(choices=PRIORITY, default="Low", max_length=50)
