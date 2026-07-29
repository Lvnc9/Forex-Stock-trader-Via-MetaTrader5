from django.contrib import admin

from apps.trading.models import Deployment


@admin.register(Deployment)
class DeploymentAdmin(admin.ModelAdmin):
    list_display = ("id", "strategy", "agent", "catalog_slug", "mt5_symbol", "status", "updated_at")
    list_filter = ("status", "agent")
    search_fields = ("strategy__name", "catalog_slug", "mt5_symbol")
