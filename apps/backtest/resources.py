"""Thermal-aware worker budgeting for backtests."""

from __future__ import annotations

import os


THERMAL_PROFILE_WORKERS = {
    "eco": 4,
    "laptop": 8,
    "max": 10,
}

BLAS_THREAD_ENV_VARS = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_MAX_THREADS",
)


def available_cpu_count() -> int:
    return max(1, os.cpu_count() or 1)


def resolve_worker_budget(*, profile_override: str | None = None) -> dict[str, int]:
    from django.conf import settings

    profile = str(profile_override or getattr(settings, "TRADEBOT_BACKTEST_THERMAL_PROFILE", "laptop")).lower()
    reserve = max(1, int(getattr(settings, "TRADEBOT_BACKTEST_CORE_RESERVE", 2)))
    fraction = float(getattr(settings, "TRADEBOT_BACKTEST_CPU_FRACTION", 0.7))
    cpu_count = available_cpu_count()
    profile_cap = THERMAL_PROFILE_WORKERS.get(profile, THERMAL_PROFILE_WORKERS["laptop"])
    auto_workers = max(1, min(int(cpu_count * fraction), cpu_count - reserve, profile_cap))

    configured_compute = int(getattr(settings, "TRADEBOT_BACKTEST_WORKERS", 0) or 0)
    compute_workers = configured_compute if configured_compute > 0 else auto_workers
    compute_workers = max(1, min(compute_workers, cpu_count - 1 if cpu_count > 1 else 1, profile_cap))

    configured_load = int(getattr(settings, "TRADEBOT_BACKTEST_LOAD_WORKERS", 0) or 0)
    load_workers = configured_load if configured_load > 0 else compute_workers
    load_workers = max(1, min(load_workers, cpu_count, profile_cap))

    configured_blas = int(getattr(settings, "TRADEBOT_BACKTEST_BLAS_THREADS", 1) or 1)
    blas_threads = max(1, configured_blas)
    return {
        "cpu_count": cpu_count,
        "profile": profile,
        "compute_workers": compute_workers,
        "load_workers": load_workers,
        "blas_threads": blas_threads,
    }


def configure_blas_threads(threads: int | None = None) -> int:
    value = max(1, int(threads or resolve_worker_budget()["blas_threads"]))
    for name in BLAS_THREAD_ENV_VARS:
        os.environ[name] = str(value)
    return value


def nice_backtest_process(increment: int = 10) -> None:
    try:
        os.nice(increment)
    except (AttributeError, OSError):
        return
