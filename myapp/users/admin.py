from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from users.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "full_name",
                    "birth_date",
                    "cpf",
                    "phone",
                    "email",
                    "apartment",
                    "block",
                    "photo",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "full_name",
                    "birth_date",
                    "cpf",
                    "phone",
                    "email",
                    "apartment",
                    "block",
                ),
            },
        ),
    )
    list_display = ("username", "full_name", "email", "apartment", "block", "is_staff")
    search_fields = ("username", "full_name", "email", "cpf")
    ordering = ("username",)
