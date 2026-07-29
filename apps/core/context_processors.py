"""Primary navigation (Phase 1a shell; routes wired in later phases)."""

NAV_ITEMS = [
    {"label": "Dashboard", "url_name": "core:dashboard", "icon": "layout-dashboard"},
    {"label": "Strategies", "url_name": None, "href": "#", "disabled": True},
    {"label": "Backtest", "url_name": None, "href": "#", "disabled": True},
    {"label": "Live trading", "url_name": None, "href": "#", "disabled": True},
    {"label": "Broker", "url_name": None, "href": "#", "disabled": True},
    {"label": "Data", "url_name": None, "href": "#", "disabled": True},
    {"label": "Settings", "url_name": None, "href": "#", "disabled": True},
]


def nav(request):
    return {"nav_items": NAV_ITEMS}
