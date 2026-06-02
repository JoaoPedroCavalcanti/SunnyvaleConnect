from django.contrib import admin

from sunny_vale_news.models import SunnyValeNewsModel


@admin.register(SunnyValeNewsModel)
class SunnyValeNewsAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "kind",
        "priority_level",
        "author",
        "author_role",
        "created_at",
    )
    list_filter = ("kind", "priority_level", "author_role")
    search_fields = ("title", "description", "author")
    readonly_fields = ("author", "author_role", "created_by", "created_at", "updated_at")
