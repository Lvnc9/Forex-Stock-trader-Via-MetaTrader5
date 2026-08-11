from __future__ import annotations

import functools
import json

from django.http import HttpRequest, JsonResponse

from apps.brokers.models import TradingAgent
from apps.brokers.tokens import hash_agent_token


def get_agent_from_request(request: HttpRequest) -> TradingAgent | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    token_digest = hash_agent_token(token)
    return TradingAgent.objects.filter(token_hash=token_digest).first()


def require_agent_api(view_func):
    @functools.wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if request.method not in ("GET", "POST"):
            return JsonResponse({"error": "method_not_allowed"}, status=405)
        agent = get_agent_from_request(request)
        if agent is None:
            return JsonResponse({"error": "unauthorized"}, status=401)
        request.trading_agent = agent
        return view_func(request, *args, **kwargs)

    return wrapper


def parse_json_body(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}
