from django.db import models
from django.utils.text import slugify

from condominiums.modules import default_enabled_modules
from shared.infrastructure.code_generator import RandomCodeGenerator

_CODE_LENGTH = 8
_MAX_CODE_ATTEMPTS = 20


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
    enabled_modules = models.JSONField(
        default=default_enabled_modules,
        blank=True,
        help_text=(
            "Optional product modules available to this condominium. "
            "Frontend only — does not gate backend APIs."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            generator = RandomCodeGenerator()
            for _ in range(_MAX_CODE_ATTEMPTS):
                candidate = generator.alphanumeric(_CODE_LENGTH)
                if not Condominium.objects.filter(code__iexact=candidate).exclude(
                    pk=self.pk
                ).exists():
                    self.code = candidate
                    break
            else:
                raise ValueError("Could not generate a unique condominium code.")

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
