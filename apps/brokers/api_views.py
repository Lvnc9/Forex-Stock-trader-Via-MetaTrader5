from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.brokers.auth import parse_json_body, require_agent_api
from apps.trading.models import Deployment


@csrf_exempt
@require_http_methods(["POST"])
@require_agent_api
def heartbeat(request):
    agent = request.trading_agent
    payload = parse_json_body(request)
    agent.mt5_connected = bool(payload.get("mt5_connected", False))
    account = payload.get("account") or {}
    if isinstance(account, dict):
        agent.account_snapshot = account
    agent.last_heartbeat_at = timezone.now()
    agent.save(
        update_fields=["mt5_connected", "account_snapshot", "last_heartbeat_at"],
    )
    return JsonResponse({"ok": True, "server_time": timezone.now().isoformat()})


@csrf_exempt
@require_http_methods(["POST"])
@require_agent_api
def sync(request):
    agent = request.trading_agent
    payload = parse_json_body(request)
    agent.sync_snapshot = {
        "positions": payload.get("positions", []),
        "deals": payload.get("deals", []),
        "errors": payload.get("errors", []),
        "deployment_state": payload.get("deployment_state", []),
    }
    agent.last_sync_at = timezone.now()
    agent.save(update_fields=["sync_snapshot", "last_sync_at"])

    for item in payload.get("deployment_state") or []:
        if not isinstance(item, dict):
            continue
        dep_id = item.get("id")
        if dep_id is None:
            continue
        Deployment.objects.filter(pk=dep_id, agent=agent).update(last_agent_report=item)
        status = item.get("status")
        if status in ("strategy_error", "no_data") or item.get("order", {}).get("ok") is False:
            from apps.trading.events import record_event
            from apps.trading.models import Deployment as DepModel

            dep = DepModel.objects.filter(pk=dep_id, agent=agent).first()
            if dep:
                record_event(
                    dep,
                    "agent_error",
                    f"Agent reported {status or 'order_error'}",
                    item,
                )

    for err in payload.get("errors") or []:
        if not isinstance(err, str):
            continue
        # Attach first matching armed dep's event stream if possible
        dep = Deployment.objects.filter(agent=agent, status=Deployment.Status.ARMED).first()
        if dep:
            from apps.trading.events import record_event

            record_event(dep, "agent_error", err[:500])

    return JsonResponse({"ok": True})


@csrf_exempt
@require_http_methods(["GET"])
@require_agent_api
def deployments(request):
    agent = request.trading_agent
    qs = Deployment.objects.filter(
        agent=agent,
        status=Deployment.Status.ARMED,
    ).select_related("strategy")

    # Live accounts only receive deployments that were explicitly live-confirmed.
    if agent.is_live_account:
        qs = qs.filter(live_confirmed=True)

    items = []
    for dep in qs:
        items.append(
            {
                "id": dep.id,
                "module_path": dep.strategy.module_path,
                "parameters": dep.parameters or dep.strategy.runtime_parameters(),
                "catalog_slug": dep.catalog_slug,
                "mt5_symbol": dep.mt5_symbol,
                "timeframe": dep.timeframe,
                "htf_timeframe": dep.htf_timeframe or "",
                "lot_size": dep.lot_size,
            }
        )
    return JsonResponse({"deployments": items})
