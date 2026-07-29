from django.urls import path

from apps.strategies.views import StrategyListView

app_name = "strategies"

urlpatterns = [
    path("", StrategyListView.as_view(), name="list"),
]
