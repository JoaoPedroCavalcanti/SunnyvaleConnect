from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from shared.tenant import build_tenant_username, display_username
from users.forms import SunnyvaleUserAddForm, SunnyvaleUserChangeForm
from users.models import User, UserRole


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = SunnyvaleUserChangeForm
    add_form = SunnyvaleUserAddForm

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
            "Condominium",
            {
                "fields": ("condominium",),
                "description": (
                    "Required for condominium accounts. Platform superusers "
                    "must leave this empty."
                ),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "employee_types",
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "description": (
                    "Set role to Admin to create a condominium administrator. "
                    "Staff access is assigned automatically from the role."
                ),
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
                    "condominium",
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
                    "role",
                    "employee_types",
                    "is_active",
                ),
            },
        ),
    )
    list_display = (
        "display_username_column",
        "full_name",
        "email",
        "condominium",
        "role",
        "is_staff",
        "is_active",
    )
    list_filter = ("condominium", "role", "is_staff", "is_active", "is_superuser")
    search_fields = ("username", "full_name", "email", "cpf")
    ordering = ("username",)
    autocomplete_fields = ("condominium",)
    list_select_related = ("condominium",)

    @admin.display(description="Username")
    def display_username_column(self, obj):
        return display_username(obj)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        condo_id = request.GET.get("condominium", "").strip()
        if condo_id.isdigit():
            initial["condominium"] = int(condo_id)
        role = (request.GET.get("role") or "").strip().upper()
        if role in UserRole.values:
            initial["role"] = role
        return initial

    def save_model(self, request, obj, form, change):
        if obj.condominium_id and obj.condominium.code:
            local = display_username(obj)
            obj.username = build_tenant_username(obj.condominium.code, local)
        if not obj.is_superuser:
            obj.is_staff = obj.role == UserRole.ADMIN
        super().save_model(request, obj, form, change)
