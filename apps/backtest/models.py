from django.db import models


class BacktestRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    strategy = models.ForeignKey(
        "strategies.Strategy",
        on_delete=models.CASCADE,
        related_name="backtest_runs",
    )
    catalog_slug = models.SlugField(max_length=80)
    timeframe = models.CharField(max_length=8, default="M5")
    start = models.DateField()
    end = models.DateField()
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2, default=10_000)
    spread_pct = models.FloatField(
        default=0.0,
        help_text="Total spread as fraction of price (e.g. 0.0002 = 0.02%).",
    )
    commission = models.FloatField(default=0.0, help_text="Flat commission per closed trade.")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
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
