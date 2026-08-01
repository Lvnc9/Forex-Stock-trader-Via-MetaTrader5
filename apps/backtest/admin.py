from django.contrib import admin

from apps.backtest.models import BacktestRun


@admin.register(BacktestRun)
class BacktestRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "strategy",
        "catalog_slug",
        "timeframe",
        "status",
        "progress_pct",
        "created_at",
    )
    list_filter = ("status", "timeframe", "catalog_slug")
    search_fields = ("strategy__name", "catalog_slug")
    readonly_fields = (
        "metrics",
        "equity_curve",
        "trades",
        "progress_pct",
        "progress_message",
        "completed_at",
        "created_at",
    )
