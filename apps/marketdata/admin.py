from django.contrib import admin

from apps.marketdata.models import SymbolMap


@admin.register(SymbolMap)
class SymbolMapAdmin(admin.ModelAdmin):
    list_display = ("catalog_slug", "dukascopy_id", "mt5_symbol", "updated_at")
    search_fields = ("catalog_slug", "dukascopy_id", "mt5_symbol")
