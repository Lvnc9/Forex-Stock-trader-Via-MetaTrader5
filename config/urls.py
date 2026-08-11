from django.contrib import admin
from django.urls import include, path

from apps.brokers import api_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("strategies/", include("apps.strategies.urls")),
    path("data/", include("apps.marketdata.urls")),
    path("backtest/", include("apps.backtest.urls")),
    path("broker/", include("apps.brokers.urls")),
    path("live/", include("apps.trading.urls")),
    path("api/agent/heartbeat", api_views.heartbeat, name="agent_heartbeat"),
    path("api/agent/sync", api_views.sync, name="agent_sync"),
    path("api/agent/deployments", api_views.deployments, name="agent_deployments"),
]
