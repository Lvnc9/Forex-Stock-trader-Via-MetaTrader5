"""Primary navigation (sidebar)."""

from apps.brokers.models import TradingAgent

NAV_ITEMS = [
    {"label": "Dashboard", "url_name": "core:dashboard"},
    {"label": "Strategies", "url_name": "strategies:list"},
    {"label": "Backtest", "url_name": "backtest:list"},
    {"label": "Live trading", "url_name": "trading:list"},
    {"label": "Broker", "url_name": "brokers:agents"},
    {"label": "Data", "url_name": "marketdata:catalog"},
    {"label": "Settings", "url_name": None, "href": "#", "disabled": True},
]


def nav(request):
    return {"nav_items": NAV_ITEMS}


def broker_status(request):
    agents = list(TradingAgent.objects.all())
    online = [a for a in agents if a.is_online]
    return {
        "broker_any_online": bool(online),
        "broker_mt5_connected": any(a.mt5_connected for a in online),
        "broker_live_mode": any(a.is_live_account for a in online),
        "broker_agent_count": len(agents),
    }
