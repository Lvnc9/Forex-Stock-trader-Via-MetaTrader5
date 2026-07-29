from django.conf import settings
from django.views.generic import TemplateView

from apps.marketdata.catalog import scan_data_root
from apps.strategies.models import Strategy


class DashboardView(TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        catalogs = scan_data_root(settings.TRADEBOT_DATA_ROOT)
        ctx["dataset_count"] = len(catalogs)
        ctx["strategy_count"] = Strategy.objects.count()
        return ctx
