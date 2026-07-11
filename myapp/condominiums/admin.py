from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from condominiums.models import Condominium
from shared.tenant import display_username
from users.models import UserRole


@admin.register(Condominium)
class CondominiumAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "slug", "is_active", "admin_count", "created_at")
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
            "Administrators",
            {"fields": ("admin_accounts_panel",)},
        ),
        ("Metadata", {"fields": ("created_at",)}),
    )

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
