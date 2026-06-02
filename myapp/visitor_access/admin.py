from django.contrib import admin

from visitor_access.models import (
    VisitorAccessModel,
    VisitorGroupMemberModel,
    VisitorGroupModel,
)


class VisitorGroupMemberInline(admin.TabularInline):
    model = VisitorGroupMemberModel
    extra = 0


@admin.register(VisitorGroupModel)
class VisitorGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "host_user", "created_at")
    search_fields = ("name", "host_user__email")
    inlines = [VisitorGroupMemberInline]


@admin.register(VisitorAccessModel)
class VisitorAccessAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "visitor_name",
        "host_user",
        "visitor_group",
        "scheduled_date",
        "all_day",
        "status",
    )
    list_filter = ("status", "all_day")
    search_fields = ("visitor_name", "email")
