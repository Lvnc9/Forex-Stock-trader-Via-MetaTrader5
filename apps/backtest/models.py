from django.db import models

from apps.backtest.broker import (
    DEFAULT_CONTRACT_SIZE,
    DEFAULT_LOT_SIZE,
    SIZING_ALL_IN,
    SIZING_FIXED_LOTS,
)


class BacktestRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class SizingMode(models.TextChoices):
        ALL_IN = SIZING_ALL_IN, "All-in (cash ÷ price)"
        FIXED_LOTS = SIZING_FIXED_LOTS, "Fixed lots (match live Deployment.lot_size)"

    strategy = models.ForeignKey(
        "strategies.Strategy",
        on_delete=models.CASCADE,
        related_name="backtest_runs",
    )
    catalog_slug = models.SlugField(max_length=80)
    timeframe = models.CharField(max_length=8, default="M5")
    htf_timeframe = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="Optional higher timeframe for multi-TF strategies (empty = none).",
    )
    start = models.DateField()
    end = models.DateField()
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2, default=10_000)
    spread_pct = models.FloatField(
        default=0.0,
        help_text="Total spread as fraction of price (e.g. 0.0002 = 0.02%).",
    )
    commission = models.FloatField(default=0.0, help_text="Flat commission per closed trade.")
    sizing_mode = models.CharField(
        max_length=16,
        choices=SizingMode.choices,
        default=SizingMode.ALL_IN,
        help_text="all_in compounds cash; fixed_lots matches live Deployment.lot_size.",
    )
    lot_size = models.FloatField(
        default=DEFAULT_LOT_SIZE,
        help_text="Used when sizing_mode=fixed_lots (same meaning as Deployment.lot_size).",
    )
    contract_size = models.FloatField(
        default=DEFAULT_CONTRACT_SIZE,
        help_text="Units per 1.0 lot (100000 for standard FX; adjust for CFDs/indices).",
    )
    parameter_overrides = models.JSONField(
        default=dict,
        blank=True,
        help_text="Merged over strategy.runtime_parameters() for this run (param sweeps).",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    progress_pct = models.FloatField(default=0.0, help_text="0–100 while running.")
    progress_message = models.CharField(max_length=240, blank=True, default="")
    metrics = models.JSONField(default=dict, blank=True)
    equity_curve = models.JSONField(default=list, blank=True)
    trades = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.strategy.name} · {self.catalog_slug} ({self.status})"

    @property
    def win_rate_pct(self) -> float | None:
        if not self.metrics:
            return None
        return self.metrics.get("win_rate_pct")
