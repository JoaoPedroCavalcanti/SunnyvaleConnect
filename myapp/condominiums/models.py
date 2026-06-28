from django.db import models
from django.utils.text import slugify


class Condominium(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    code = models.CharField(max_length=8, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    primary_color = models.CharField(max_length=7, default="#d97706")
    secondary_color = models.CharField(max_length=7, default="#1e40af")
    accent_color = models.CharField(max_length=7, default="#111827")
    logo = models.ImageField(upload_to="condominiums/logos/", blank=True, null=True)
    welcome_message = models.CharField(max_length=300, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "condominium"
            candidate = base
            suffix = 1
            while (
                Condominium.objects.filter(slug=candidate)
                .exclude(pk=self.pk)
                .exists()
            ):
                suffix += 1
                candidate = f"{base}-{suffix}"
            self.slug = candidate
        super().save(*args, **kwargs)
