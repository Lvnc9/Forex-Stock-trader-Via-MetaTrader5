from __future__ import annotations

import importlib
from typing import Type

from django.core.exceptions import ValidationError

from apps.strategies.base import BaseStrategy


def load_strategy_class(module_path: str) -> Type[BaseStrategy]:
    if not module_path.startswith("apps.strategies."):
        raise ValidationError(f"Module path must live under apps.strategies: {module_path}")
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ValidationError(f"Cannot import strategy module {module_path}: {exc}") from exc

    for attr_name in dir(module):
        obj = getattr(module, attr_name)
        if (
            isinstance(obj, type)
            and issubclass(obj, BaseStrategy)
            and obj is not BaseStrategy
            and getattr(obj, "module_path", "") == module_path
        ):
            return obj

    raise ValidationError(f"No BaseStrategy subclass found in {module_path}")


def instantiate_strategy(module_path: str, parameters: dict | None = None) -> BaseStrategy:
    cls = load_strategy_class(module_path)
    return cls(parameters=parameters)
