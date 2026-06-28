from django.contrib import admin

from condominiums.models import Condominium


@admin.register(Condominium)
class CondominiumAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "slug")
    readonly_fields = ("code", "slug", "created_at")
