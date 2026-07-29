from django.conf import settings
from django.views.generic import TemplateView

from apps.backtest.models import BacktestRun
from apps.brokers.models import TradingAgent
from apps.marketdata.catalog import scan_data_root
from apps.strategies.models import Strategy
from apps.trading.models import Deployment


class DashboardView(TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        catalogs = scan_data_root(settings.TRADEBOT_DATA_ROOT)
        ctx["dataset_count"] = len(catalogs)
        ctx["strategy_count"] = Strategy.objects.count()
        ctx["armed_deployments"] = Deployment.objects.filter(status=Deployment.Status.ARMED).count()
        ctx["online_agents"] = sum(1 for a in TradingAgent.objects.all() if a.is_online)
        last = (
            BacktestRun.objects.filter(status=BacktestRun.Status.COMPLETED)
            .order_by("-completed_at")
            .first()
        )
        ctx["last_backtest"] = last
        return ctx
