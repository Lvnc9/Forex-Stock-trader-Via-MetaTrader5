from __future__ import annotations

import importlib
from typing import Type

from django.core.exceptions import ValidationError

from apps.strategies.base import BaseStrategy


def load_strategy_class(module_path: str) -> Type[BaseStrategy]:
    allowed = ("apps.strategies.library.", "apps.strategies.user.")
    if not module_path.startswith(allowed):
        raise ValidationError(f"Module path must live under apps.strategies library or user: {module_path}")
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ValidationError(f"Cannot import strategy module {module_path}: {exc}") from exc

    candidates: list[Type[BaseStrategy]] = []
    for attr_name in dir(module):
        obj = getattr(module, attr_name)
        if isinstance(obj, type) and issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
            candidates.append(obj)

    if not candidates:
        raise ValidationError(f"No BaseStrategy subclass found in {module_path}")

    for obj in candidates:
        if getattr(obj, "module_path", "") == module_path:
            return obj

    if len(candidates) == 1:
        return candidates[0]

    raise ValidationError(f"Multiple strategy classes in {module_path}; set module_path on one class.")


def instantiate_strategy(module_path: str, parameters: dict | None = None) -> BaseStrategy:
    cls = load_strategy_class(module_path)
    return cls(parameters=parameters)
