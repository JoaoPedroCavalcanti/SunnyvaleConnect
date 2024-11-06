from django.db import models


# Create your models here.
class SunnyValeNewsModel(models.Model):
    PRIORITY = [("low", "Low"), ("medium", "Medium"), ("high", "High")]

    title = (models.CharField(max_length=200),)
    description = models.TextField()
    author = models.CharField(max_length=50)
    priority_level = models.CharField(choices=PRIORITY, max_length=50, default="low")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
