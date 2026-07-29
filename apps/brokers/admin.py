from django.contrib import admin

from apps.brokers.models import TradingAgent


@admin.register(TradingAgent)
class TradingAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "is_online", "mt5_connected", "last_heartbeat_at", "created_at")
    readonly_fields = ("token_hash", "last_heartbeat_at", "account_snapshot", "last_sync_at", "sync_snapshot")

    @admin.display(boolean=True)
    def is_online(self, obj: TradingAgent) -> bool:
        return obj.is_online
