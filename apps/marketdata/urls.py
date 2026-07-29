from django.urls import path

from apps.marketdata.views import DataCatalogView

app_name = "marketdata"

urlpatterns = [
    path("", DataCatalogView.as_view(), name="catalog"),
]
