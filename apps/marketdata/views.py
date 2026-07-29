from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from apps.marketdata.catalog import scan_data_root
from apps.marketdata.models import SymbolMap


@method_decorator(login_required, name="dispatch")
class DataCatalogView(TemplateView):
    template_name = "marketdata/catalog.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        catalogs = scan_data_root(settings.TRADEBOT_DATA_ROOT)
        maps = {m.catalog_slug: m for m in SymbolMap.objects.all()}
        rows = []
        for item in catalogs:
            sym = maps.get(item.slug)
            rows.append(
                {
                    "catalog": item,
                    "symbol_map": sym,
                }
            )
        ctx["instruments"] = rows
        ctx["instrument_count"] = len(rows)
        ctx["total_bars"] = sum(row["catalog"].bar_count for row in rows)
        return ctx
