"""Optional multicore helpers for independent backtest workloads."""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any


def default_worker_count() -> int:
    try:
        from django.conf import settings

        configured = int(getattr(settings, "TRADEBOT_BACKTEST_WORKERS", 0) or 0)
        if configured > 0:
            return configured
    except Exception:
        pass
    cpu = os.cpu_count() or 2
    # Leave one core for the web process / OS.
    return max(1, min(cpu - 1, 8))


def run_jobs_multiprocess(
    jobs: list[dict[str, Any]],
    worker_fn_qualname: str,
    *,
    max_workers: int | None = None,
) -> list[Any]:
    """Run independent job dicts in a process pool.

    *worker_fn_qualname* must be an importable ``module:function`` that accepts
    a single job dict and returns a picklable result. Used for parameter sweeps;
    a single UI backtest still runs in one process (bar loop is sequential).
    """
    if not jobs:
        return []
    workers = max_workers or default_worker_count()
    workers = max(1, min(workers, len(jobs)))
    if workers == 1:
        fn = _import_fn(worker_fn_qualname)
        return [fn(job) for job in jobs]

    results: list[Any | None] = [None] * len(jobs)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_mp_entry, worker_fn_qualname, job): idx for idx, job in enumerate(jobs)
        }
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()
    return results


def _import_fn(qualname: str):
    module_name, _, attr = qualname.partition(":")
    if not module_name or not attr:
        raise ValueError(f"Expected 'module:function', got {qualname!r}")
    import importlib

    module = importlib.import_module(module_name)
    return getattr(module, attr)


def _mp_entry(qualname: str, job: dict[str, Any]):
    return _import_fn(qualname)(job)
