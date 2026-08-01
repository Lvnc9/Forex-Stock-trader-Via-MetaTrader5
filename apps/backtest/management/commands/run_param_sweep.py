"""Enqueue a small parameter sweep (multiprocess over independent runs)."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from apps.backtest.models import BacktestRun
from apps.backtest.sweep import MAX_SWEEP_JOBS, build_override_dicts, parse_param_values
from apps.backtest.tasks import enqueue_sweep
from apps.strategies.models import Strategy


class Command(BaseCommand):
    help = (
        "Create and run a small parameter sweep (≤ "
        f"{MAX_SWEEP_JOBS} jobs) via multiprocess pool. "
        "Example: --param fast_period --values 5,10,15"
    )

    def add_arguments(self, parser):
        parser.add_argument("--strategy", required=True, help="Strategy slug")
        parser.add_argument("--catalog", required=True, help="Catalog slug")
        parser.add_argument("--timeframe", default="M5")
        parser.add_argument("--htf", default="", help="Optional HTF")
        parser.add_argument("--start", required=True, help="YYYY-MM-DD")
        parser.add_argument("--end", required=True, help="YYYY-MM-DD")
        parser.add_argument("--param", required=True, help="Parameter name to sweep")
        parser.add_argument("--values", required=True, help="Comma-separated values")
        parser.add_argument("--balance", type=float, default=10_000.0)
        parser.add_argument(
            "--sizing",
            choices=["all_in", "fixed_lots"],
            default="all_in",
        )
        parser.add_argument("--lot-size", type=float, default=0.01)
        parser.add_argument("--contract-size", type=float, default=100_000.0)
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Force in-process sweep even if Celery async is configured",
        )

    def handle(self, *args, **options):
        try:
            strategy = Strategy.objects.get(slug=options["strategy"])
        except Strategy.DoesNotExist as exc:
            raise CommandError(f"Unknown strategy slug {options['strategy']!r}") from exc

        start = parse_date(options["start"])
        end = parse_date(options["end"])
        if not start or not end:
            raise CommandError("--start/--end must be YYYY-MM-DD")
        if end < start:
            raise CommandError("end must be on/after start")

        try:
            values = parse_param_values(options["values"])
            overrides_list = build_override_dicts(options["param"], values)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        runs: list[BacktestRun] = []
        for overrides in overrides_list:
            run = BacktestRun.objects.create(
                strategy=strategy,
                catalog_slug=options["catalog"],
                timeframe=options["timeframe"],
                htf_timeframe=options["htf"] or "",
                start=start,
                end=end,
                initial_balance=options["balance"],
                sizing_mode=options["sizing"],
                lot_size=options["lot_size"],
                contract_size=options["contract_size"],
                parameter_overrides=overrides,
                status=BacktestRun.Status.PENDING,
                progress_message="Queued (sweep)",
            )
            runs.append(run)
            self.stdout.write(f"Created run {run.pk} overrides={overrides}")

        if options["sync"]:
            from apps.backtest.sweep import execute_sweep_run_ids

            results = execute_sweep_run_ids([r.pk for r in runs])
            for row in results:
                self.stdout.write(
                    f"run={row['run_id']} status={row['status']} "
                    f"win={row.get('win_rate_pct')} ret={row.get('net_return_pct')}"
                )
        else:
            enqueue_sweep(runs)
            self.stdout.write(self.style.SUCCESS(f"Enqueued {len(runs)} sweep runs"))
