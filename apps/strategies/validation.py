from __future__ import annotations

import ast
import importlib
import uuid
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.strategies.engine import SignalEngine
from apps.strategies.loader import load_strategy_class

USER_MODULE_PREFIX = "apps.strategies.user."
FORBIDDEN_AST_NAMES = {"exec", "eval", "open", "__import__", "compile", "breakpoint"}


def user_strategies_dir() -> Path:
    path = Path(settings.BASE_DIR) / "apps" / "strategies" / "user"
    path.mkdir(parents=True, exist_ok=True)
    return path


def check_custom_strategy_source(source: str) -> None:
    if not source.strip():
        raise ValidationError("Strategy code is empty.")
    if "BaseStrategy" not in source:
        raise ValidationError("Custom strategy must subclass BaseStrategy.")
    if "def on_bar" not in source:
        raise ValidationError("Custom strategy must implement on_bar().")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_AST_NAMES:
            raise ValidationError(f"Forbidden name in strategy code: {node.id}")


def _sample_bars(rows: int = 80) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=rows, freq="5min", tz="UTC")
    close = pd.Series([100 + (i % 15) * 0.5 for i in range(rows)], index=index, dtype=float)
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close},
        index=index,
    )


def install_custom_strategy_source(source: str) -> str:
    """Write module, import, dry-run. Returns ``module_path``."""
    check_custom_strategy_source(source)

    module_name = f"custom_{uuid.uuid4().hex[:12]}"
    module_path = f"{USER_MODULE_PREFIX}{module_name}"
    file_path = user_strategies_dir() / f"{module_name}.py"
    file_path.write_text(source.strip() + "\n", encoding="utf-8")

    try:
        importlib.invalidate_caches()
        cls = load_strategy_class(module_path)
        instance = cls()
        SignalEngine().run(instance, _sample_bars(), warmup=10)
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        raise ValidationError(f"Validation failed: {exc}") from exc

    return module_path


def update_custom_strategy_source(module_path: str, source: str) -> str:
    """Edit an existing user module in place; roll back file on validation failure."""
    check_custom_strategy_source(source)
    if not module_path.startswith(USER_MODULE_PREFIX):
        raise ValidationError("Can only update user strategy modules.")

    module_name = module_path.removeprefix(USER_MODULE_PREFIX)
    if not module_name or "/" in module_name or "\\" in module_name or "." in module_name:
        raise ValidationError("Invalid user module path.")

    file_path = user_strategies_dir() / f"{module_name}.py"
    previous = file_path.read_text(encoding="utf-8") if file_path.exists() else None
    file_path.write_text(source.strip() + "\n", encoding="utf-8")

    try:
        importlib.invalidate_caches()
        # Drop cached module so re-import picks up new source.
        import sys

        sys.modules.pop(module_path, None)
        cls = load_strategy_class(module_path)
        instance = cls()
        SignalEngine().run(instance, _sample_bars(), warmup=10)
    except Exception as exc:
        if previous is None:
            file_path.unlink(missing_ok=True)
        else:
            file_path.write_text(previous, encoding="utf-8")
        raise ValidationError(f"Validation failed: {exc}") from exc

    return module_path


def dry_run_rule_spec(spec: dict, parameters: dict | None = None) -> None:
    """Validate rule_spec by running RuleStrategy on synthetic bars."""
    from apps.strategies.rules.runtime import RULE_SPEC_KEY, RuleStrategy

    params = dict(parameters or {})
    params[RULE_SPEC_KEY] = spec
    instance = RuleStrategy(params)
    SignalEngine().run(instance, _sample_bars(), warmup=10)
