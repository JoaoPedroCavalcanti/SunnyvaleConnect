from django.contrib import admin

from reservations.models import ReservableLocation, Reservation


class PlatformSuperuserAdminMixin:
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReservableLocation)
class ReservableLocationAdmin(
    PlatformSuperuserAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "condominium",
        "icon",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active", "condominium")
    search_fields = ("name", "description", "condominium__name")
    list_select_related = ("condominium",)
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "condominium",
        "name",
        "description",
        "icon",
        "is_active",
        "created_at",
        "updated_at",
    )


@admin.register(Reservation)
class ReservationAdmin(
    PlatformSuperuserAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "location",
        "condominium",
        "reservation_date",
        "start_time",
        "end_time",
        "status",
        "reservation_user",
        "unit",
    )
    list_filter = (
        "status",
        "reservation_date",
        "location",
        "condominium",
    )
    search_fields = (
        "location__name",
        "reservation_user__username",
        "reservation_user__email",
    )
    list_select_related = (
        "location",
        "condominium",
        "reservation_user",
        "unit",
    )
    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
