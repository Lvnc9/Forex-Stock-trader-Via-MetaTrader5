from django.urls import path

from apps.marketdata.views import (
    DataCatalogView,
    SymbolMapCreateView,
    SymbolMapDeleteView,
    SymbolMapListView,
    SymbolMapUpdateView,
)

app_name = "marketdata"

urlpatterns = [
    path("", DataCatalogView.as_view(), name="catalog"),
    path("symbols/", SymbolMapListView.as_view(), name="symbol_maps"),
    path("symbols/new/", SymbolMapCreateView.as_view(), name="symbol_map_create"),
    path("symbols/<int:pk>/edit/", SymbolMapUpdateView.as_view(), name="symbol_map_edit"),
    path("symbols/<int:pk>/delete/", SymbolMapDeleteView.as_view(), name="symbol_map_delete"),
]
