from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.marketdata.catalog import scan_data_root
from apps.marketdata.forms import SymbolMapForm
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


@method_decorator(login_required, name="dispatch")
class SymbolMapListView(ListView):
    model = SymbolMap
    template_name = "marketdata/symbol_maps.html"
    context_object_name = "maps"


@method_decorator(login_required, name="dispatch")
class SymbolMapCreateView(View):
    template_name = "marketdata/symbol_map_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": SymbolMapForm(), "is_edit": False})

    def post(self, request):
        form = SymbolMapForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "is_edit": False})
        form.save()
        messages.success(request, "Symbol map saved.")
        return redirect("marketdata:symbol_maps")


@method_decorator(login_required, name="dispatch")
class SymbolMapUpdateView(View):
    template_name = "marketdata/symbol_map_form.html"

    def get(self, request, pk):
        obj = get_object_or_404(SymbolMap, pk=pk)
        return render(
            request,
            self.template_name,
            {"form": SymbolMapForm(instance=obj), "is_edit": True, "obj": obj},
        )

    def post(self, request, pk):
        obj = get_object_or_404(SymbolMap, pk=pk)
        form = SymbolMapForm(request.POST, instance=obj)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "is_edit": True, "obj": obj},
            )
        form.save()
        messages.success(request, "Symbol map updated.")
        return redirect("marketdata:symbol_maps")


@method_decorator(login_required, name="dispatch")
class SymbolMapDeleteView(View):
    def post(self, request, pk):
        obj = get_object_or_404(SymbolMap, pk=pk)
        obj.delete()
        messages.success(request, "Symbol map deleted.")
        return redirect("marketdata:symbol_maps")
