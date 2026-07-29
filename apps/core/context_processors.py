"""Primary navigation (sidebar)."""

NAV_ITEMS = [
    {"label": "Dashboard", "url_name": "core:dashboard"},
    {"label": "Strategies", "url_name": "strategies:list"},
    {"label": "Backtest", "url_name": None, "href": "#", "disabled": True},
    {"label": "Live trading", "url_name": None, "href": "#", "disabled": True},
    {"label": "Broker", "url_name": None, "href": "#", "disabled": True},
    {"label": "Data", "url_name": "marketdata:catalog"},
    {"label": "Settings", "url_name": None, "href": "#", "disabled": True},
]


def nav(request):
    return {"nav_items": NAV_ITEMS}
