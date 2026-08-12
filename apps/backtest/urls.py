from django.urls import path

from apps.backtest.views import (
    BacktestCompareView,
    BacktestCreateView,
    BacktestDeleteView,
    BacktestDetailView,
    BacktestListView,
    BacktestStatusView,
    BacktestSweepCreateView,
)

app_name = "backtest"

urlpatterns = [
    path("", BacktestListView.as_view(), name="list"),
    path("new/", BacktestCreateView.as_view(), name="create"),
    path("sweep/", BacktestSweepCreateView.as_view(), name="sweep"),
    path("compare/", BacktestCompareView.as_view(), name="compare"),
    path("<int:pk>/status/", BacktestStatusView.as_view(), name="status"),
    path("<int:pk>/delete/", BacktestDeleteView.as_view(), name="delete"),
    path("<int:pk>/", BacktestDetailView.as_view(), name="detail"),
]

