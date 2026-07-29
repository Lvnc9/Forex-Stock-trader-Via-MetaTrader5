from django.urls import path

from apps.backtest.views import BacktestCompareView, BacktestCreateView, BacktestDetailView, BacktestListView

app_name = "backtest"

urlpatterns = [
    path("", BacktestListView.as_view(), name="list"),
    path("new/", BacktestCreateView.as_view(), name="create"),
    path("compare/", BacktestCompareView.as_view(), name="compare"),
    path("<int:pk>/", BacktestDetailView.as_view(), name="detail"),
]
