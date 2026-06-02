from django.contrib import admin

from service_requests.models import ServiceRequestModel


@admin.register(ServiceRequestModel)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "requester",
        "service_type",
        "priority",
        "status",
        "responded_by",
        "created_at",
    )
    list_filter = ("status", "priority", "service_type")
    search_fields = ("title", "description", "requester__username")
    readonly_fields = ("created_at", "updated_at", "responded_at")
