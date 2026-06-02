from django.conf import settings
from django.db import models


class SunnyValeNewsModel(models.Model):
    class Kind(models.TextChoices):
        NOTICE = "NOTICE", "Aviso"
        MAINTENANCE = "MAINTENANCE", "Manutenção"
        EVENT = "EVENT", "Evento"

    PRIORITY = [("low", "Low"), ("medium", "Medium"), ("high", "High")]

    title = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField()
    kind = models.CharField(
        max_length=20, choices=Kind.choices, default=Kind.NOTICE
    )
    priority_level = models.CharField(
        choices=PRIORITY, max_length=50, default="low"
    )

    # Authorship: live FK plus denormalized snapshots so the listing
    # keeps rendering "criado por João Pedro · Administrador" even after
    # the author user is deleted.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_created",
    )
    author = models.CharField(max_length=150, blank=True, default="")
    author_role = models.CharField(max_length=20, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
