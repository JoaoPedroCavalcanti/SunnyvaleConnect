from django.contrib import admin

from households.models import Dependent, Household, HouseholdMembership


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("id", "apartment", "block", "status", "created_at")
    list_filter = ("status", "block")
    search_fields = ("apartment", "block")


@admin.register(HouseholdMembership)
class HouseholdMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "user", "role", "status", "joined_at")
    list_filter = ("role", "status")
    search_fields = ("user__username", "user__full_name")


@admin.register(Dependent)
class DependentAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "full_name", "relationship", "is_active")
    list_filter = ("is_active",)
    search_fields = ("full_name", "cpf")
