from django.db import models


class Deployment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ARMED = "armed", "Armed"
        PAUSED = "paused", "Paused"
        STOPPED = "stopped", "Stopped"

    strategy = models.ForeignKey(
        "strategies.Strategy",
        on_delete=models.CASCADE,
        related_name="deployments",
    )
    agent = models.ForeignKey(
        "brokers.TradingAgent",
        on_delete=models.CASCADE,
        related_name="deployments",
    )
    catalog_slug = models.SlugField(max_length=80)
    mt5_symbol = models.CharField(max_length=64)
    timeframe = models.CharField(max_length=8, default="M5")
    lot_size = models.FloatField(default=0.01)
    parameters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    live_confirmed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.strategy.name} → {self.agent.name} ({self.status})"
