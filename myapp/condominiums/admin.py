from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from condominiums.models import Condominium
from condominiums.modules import (
    ALL_MODULE_KEYS,
    MODULE_CHOICES,
    normalize_enabled_modules,
)
from shared.tenant import display_username
from users.models import UserRole


class CondominiumAdminForm(forms.ModelForm):
    enable_all_modules = forms.BooleanField(
        required=False,
        label="Todos os módulos",
        help_text=(
            "Atalho: marca/desmarca todos abaixo. "
            "O que vale ao salvar são os checkboxes individuais."
        ),
    )
    enabled_modules = forms.MultipleChoiceField(
        choices=MODULE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Módulos liberados",
        help_text=(
            "Usado só pelo front (menus/telas). Não bloqueia APIs no backend."
        ),
    )

    class Meta:
        model = Condominium
        fields = "__all__"

    class Media:
        js = ("condominiums/admin_modules.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = list(ALL_MODULE_KEYS)
        if self.instance and self.instance.pk:
            raw = self.instance.enabled_modules
            if isinstance(raw, list):
                current = [key for key in ALL_MODULE_KEYS if key in raw]
        elif not (self.instance and self.instance.pk):
            current = list(ALL_MODULE_KEYS)
        self.fields["enabled_modules"].initial = current
        self.fields["enable_all_modules"].initial = set(current) == set(
            ALL_MODULE_KEYS
        )

    def clean(self):
        cleaned = super().clean()
        # Individual checkboxes are the source of truth. "enable_all_modules"
        # is only a UI shortcut (synced via JS) and must not override a subset.
        try:
            cleaned["enabled_modules"] = normalize_enabled_modules(
                cleaned.get("enabled_modules") or []
            )
        except ValueError as exc:
            raise forms.ValidationError({"enabled_modules": str(exc)}) from exc
        return cleaned


@admin.register(Condominium)
class CondominiumAdmin(admin.ModelAdmin):
    form = CondominiumAdminForm
    list_display = (
        "name",
        "code",
        "slug",
        "is_active",
        "modules_summary",
        "admin_count",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "code", "slug")
    readonly_fields = ("code", "slug", "created_at", "admin_accounts_panel")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "code",
                    "slug",
                    "is_active",
                    "welcome_message",
                )
            },
        ),
        (
            "Branding",
            {
                "fields": (
                    "primary_color",
                    "secondary_color",
                    "accent_color",
                    "logo",
                )
            },
        ),
        (
            "Módulos",
            {
                "fields": ("enable_all_modules", "enabled_modules"),
                "description": (
                    "Escolha quais módulos o condomínio verá no app. "
                    "Você pode editar depois para liberar ou remover módulos."
                ),
            },
        ),
        (
            "Administrators",
            {"fields": ("admin_accounts_panel",)},
        ),
        ("Metadata", {"fields": ("created_at",)}),
    )

    @admin.display(description="Módulos")
    def modules_summary(self, obj):
        enabled = obj.enabled_modules or []
        if set(enabled) >= set(ALL_MODULE_KEYS):
            return "Todos"
        return f"{len(enabled)}/{len(ALL_MODULE_KEYS)}"

    @admin.display(description="Admins")
    def admin_count(self, obj):
        return obj.users.filter(role=UserRole.ADMIN).count()

    @admin.display(description="Condominium administrators")
    def admin_accounts_panel(self, obj):
        if not obj.pk:
            return "Save the condominium first, then add administrators."

        admins = obj.users.filter(role=UserRole.ADMIN).order_by("full_name", "email")
        if admins:
            list_html = format_html(
                "<ul>{}</ul>",
                format_html_join(
                    "",
                    '<li><a href="{}">{}</a> &mdash; {}</li>',
                    (
                        (
                            reverse("admin:users_user_change", args=[user.pk]),
                            user.full_name or display_username(user),
                            user.email,
                        )
                        for user in admins
                    ),
                ),
            )
        else:
            list_html = format_html("<p>No administrators yet.</p>")
        add_url = (
            reverse("admin:users_user_add")
            + f"?condominium={obj.pk}&role={UserRole.ADMIN}"
        )
        return format_html(
            "{}{}",
            list_html,
            format_html(
                '<p><a class="button" href="{}">Add condominium admin</a></p>',
                add_url,
            ),
        )
