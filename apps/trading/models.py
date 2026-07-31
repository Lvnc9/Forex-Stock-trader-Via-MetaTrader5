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
    htf_timeframe = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="Optional higher timeframe bars for multi-TF strategies (empty = none).",
    )
    lot_size = models.FloatField(default=0.01)
    parameters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    live_confirmed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    last_agent_report = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.strategy.name} → {self.agent.name} ({self.status})"


class DeploymentEvent(models.Model):
    """Append-only audit log for deployment lifecycle and agent errors."""

    deployment = models.ForeignKey(
        Deployment,
        on_delete=models.CASCADE,
        related_name="events",
    )
    kind = models.CharField(max_length=32)
    message = models.CharField(max_length=500, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.deployment_id}:{self.kind}"
