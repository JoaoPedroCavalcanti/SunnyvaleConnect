from django.contrib import admin

from units.models import Unit, UnitMembership


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "kind",
        "display_name",
        "status",
        "condominium",
        "created_at",
    )
    list_filter = ("kind", "status", "condominium")
    search_fields = ("name", "apartment", "block")
    raw_id_fields = ("condominium",)

    fieldsets = (
        (None, {"fields": ("condominium", "status")}),
        (
            "Kind",
            {
                "fields": ("kind", "name", "apartment", "block"),
                "description": (
                    "NAMED: name only. APARTMENT: apartment only. "
                    "APARTMENT_BLOCK: apartment + block."
                ),
            },
        ),
    )


@admin.register(UnitMembership)
class UnitMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "unit", "user", "role", "status", "joined_at")
    list_filter = ("role", "status")
    search_fields = ("user__username", "user__full_name")
    raw_id_fields = ("unit", "user")
