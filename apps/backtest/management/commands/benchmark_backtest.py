"""Benchmark a single backtest locally and print phase timings."""

from __future__ import annotations

import time
from datetime import datetime, time as dt_time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.backtest.data_handler import BacktestDataHandler
from apps.backtest.resources import configure_blas_threads, nice_backtest_process, resolve_worker_budget
from apps.backtest.runner import BacktestRunner
from apps.strategies.loader import instantiate_strategy
from apps.strategies.models import Strategy


class Command(BaseCommand):
    help = "Benchmark one backtest locally and report phase timings."

    def add_arguments(self, parser):
        parser.add_argument("--strategy", required=True, help="Strategy slug")
        parser.add_argument("--catalog", required=True, help="Catalog slug")
        parser.add_argument("--timeframe", default="M5")
        parser.add_argument("--htf", default="", help="Optional HTF timeframe")
        parser.add_argument("--days", type=int, default=90, help="Trailing days to load")
        parser.add_argument("--end", default="", help="Optional YYYY-MM-DD end date")
        parser.add_argument("--balance", type=float, default=10_000.0)
        parser.add_argument("--profile", default="", help="Optional thermal profile: eco, laptop, max")

    def handle(self, *args, **options):
        try:
            strategy_row = Strategy.objects.get(slug=options["strategy"])
        except Strategy.DoesNotExist as exc:
            raise CommandError(f"Unknown strategy slug {options['strategy']!r}") from exc

        budget = resolve_worker_budget(profile_override=options["profile"] or None)
        configure_blas_threads(budget["blas_threads"])
        nice_backtest_process()

        end_dt = self._resolve_end(options["end"])
        start_dt = end_dt - timedelta(days=int(options["days"]))

        params = strategy_row.runtime_parameters()
        strategy = instantiate_strategy(strategy_row.module_path, params)
        handler = BacktestDataHandler(
            settings.TRADEBOT_DATA_ROOT,
            max_workers=budget["load_workers"],
            use_cache=bool(getattr(settings, "TRADEBOT_BACKTEST_CACHE", True)),
        )

        t0 = time.perf_counter()
        bars, htf_bars, _meta = handler.load(
            options["catalog"],
            options["timeframe"],
            htf_timeframe=options["htf"] or None,
            start=start_dt,
            end=end_dt,
        )
        t1 = time.perf_counter()
        result = BacktestRunner().run(
            strategy,
            bars,
            htf_bars=htf_bars,
            initial_balance=float(options["balance"]),
        )
        t2 = time.perf_counter()

        self.stdout.write(
            self.style.SUCCESS(
                "benchmark "
                f"load={t1 - t0:.3f}s "
                f"run={t2 - t1:.3f}s "
                f"total={t2 - t0:.3f}s "
                f"bars={len(bars)} "
                f"load_workers={budget['load_workers']} "
                f"compute_workers={budget['compute_workers']} "
                f"trades={len(result.trades)} "
                f"win_rate={result.metrics.get('win_rate_pct')}"
            )
        )

    def _resolve_end(self, raw: str) -> datetime:
        if raw:
            parsed = datetime.fromisoformat(raw)
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed)
            return parsed
        today = timezone.now().date()
        return timezone.make_aware(datetime.combine(today, dt_time.max))
