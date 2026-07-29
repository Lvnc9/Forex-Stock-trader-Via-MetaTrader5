from django.contrib import admin

from apps.trading.models import Deployment, DeploymentEvent


@admin.register(Deployment)
class DeploymentAdmin(admin.ModelAdmin):
    list_display = ("id", "strategy", "agent", "catalog_slug", "mt5_symbol", "status", "live_confirmed", "updated_at")
    list_filter = ("status", "agent")
    search_fields = ("strategy__name", "catalog_slug", "mt5_symbol")


@admin.register(DeploymentEvent)
class DeploymentEventAdmin(admin.ModelAdmin):
    list_display = ("id", "deployment", "kind", "message", "created_at")
    list_filter = ("kind",)
    search_fields = ("message",)
