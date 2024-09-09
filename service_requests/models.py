from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.
class ServiceRequestModel(models.Model):
    
    PRIORITY_LEVEL = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        # Add more choices here as needed
    ]
    STATUS = [
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        # Add more choices here as needed
    ]
    
    requester_user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    request_description = models.TextField(blank=True, null=True, default="")
    service_type = models.CharField(max_length=150, default="Other")
    location = models.CharField(max_length=150, blank=True, null=True, default="")
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_LEVEL,
        default='low'
    )
    request_scheduled_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Staff will fill these fields
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='requested'
    )
    responsable_staff = models.CharField(max_length=50, blank=True, null=True, default="")
    scheduled_date = models.DateTimeField(blank=True, null=True)
    more_details = models.TextField(max_length=200, blank=True, null=True, default="")