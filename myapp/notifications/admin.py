from django.contrib import admin

from notifications.models import NotificationModel


@admin.register(NotificationModel)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "type",
        "title",
        "recipient",
        "condominium",
        "read_at",
        "created_at",
    )
    list_filter = ("type", "condominium")
    search_fields = ("title", "body", "recipient__email")
    readonly_fields = ("created_at",)
