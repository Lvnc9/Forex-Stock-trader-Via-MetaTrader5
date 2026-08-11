from __future__ import annotations

from typing import Any

from apps.trading.models import Deployment, DeploymentEvent


def record_event(
    deployment: Deployment,
    kind: str,
    message: str = "",
    payload: dict[str, Any] | None = None,
) -> DeploymentEvent:
    return DeploymentEvent.objects.create(
        deployment=deployment,
        kind=kind,
        message=message[:500],
        payload=payload or {},
    )
