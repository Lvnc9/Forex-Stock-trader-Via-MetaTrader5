from django.contrib import admin

from apps.strategies.models import Strategy


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "module_path", "is_library", "updated_at")
    search_fields = ("name", "module_path", "slug")
    list_filter = ("is_library",)
