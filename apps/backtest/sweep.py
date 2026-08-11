"""Parameter sweep helpers — multiprocess over independent runs, not the bar loop."""

from __future__ import annotations

import ast
from typing import Any

from apps.backtest.parallel import run_jobs_multiprocess

# Keep UI / CLI sweeps small so a Celery worker stays healthy.
MAX_SWEEP_JOBS = 8


def parse_param_values(raw: str) -> list[Any]:
    """Parse comma-separated values; ints/floats preferred, else strings."""
    parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
    if not parts:
        raise ValueError("Provide at least one parameter value.")
    if len(parts) > MAX_SWEEP_JOBS:
        raise ValueError(f"At most {MAX_SWEEP_JOBS} sweep values allowed.")
    out: list[Any] = []
    for part in parts:
        try:
            out.append(ast.literal_eval(part))
        except (ValueError, SyntaxError):
            out.append(part)
    return out


def build_override_dicts(param_name: str, values: list[Any]) -> list[dict]:
    name = (param_name or "").strip()
    if not name:
        raise ValueError("Parameter name is required.")
    if not values:
        raise ValueError("At least one value is required.")
    if len(values) > MAX_SWEEP_JOBS:
        raise ValueError(f"At most {MAX_SWEEP_JOBS} sweep values allowed.")
    return [{name: v} for v in values]


def execute_sweep_run_ids(
    run_ids: list[int],
    *,
    max_workers: int | None = None,
) -> list[dict]:
    """Run independent BacktestRun rows via process pool (bar loop stays sequential)."""
    jobs = [{"run_id": int(rid)} for rid in run_ids]
    return run_jobs_multiprocess(
        jobs,
        "apps.backtest.sweep:sweep_worker",
        max_workers=max_workers,
    )


def sweep_worker(job: dict) -> dict:
    """Process-pool entry: load Django, execute one BacktestRun by id."""
    import django
    from django.apps import apps

    if not apps.ready:
        django.setup()

    from apps.backtest.models import BacktestRun
    from apps.backtest.services import execute_backtest

    run_id = int(job["run_id"])
    run = BacktestRun.objects.select_related("strategy").get(pk=run_id)
    execute_backtest(run)
    run.refresh_from_db()
    return {
        "run_id": run.pk,
        "status": run.status,
        "parameter_overrides": run.parameter_overrides or {},
        "win_rate_pct": (run.metrics or {}).get("win_rate_pct"),
        "net_return_pct": (run.metrics or {}).get("net_return_pct"),
        "error_message": run.error_message,
    }
