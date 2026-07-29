from django.conf import settings
from django.db import models
from django.utils import timezone


class TradingAgent(models.Model):
    name = models.CharField(max_length=120, unique=True)
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    mt5_connected = models.BooleanField(default=False)
    account_snapshot = models.JSONField(default=dict, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_online(self) -> bool:
        if not self.last_heartbeat_at:
            return False
        ttl = getattr(settings, "AGENT_HEARTBEAT_TTL_SECONDS", 90)
        return (timezone.now() - self.last_heartbeat_at).total_seconds() <= ttl

    @property
    def trade_mode(self) -> str:
        mode = (self.account_snapshot or {}).get("trade_mode", "unknown")
        return str(mode).lower()

    @property
    def is_live_account(self) -> bool:
        return self.trade_mode in ("live", "real", "contest")
