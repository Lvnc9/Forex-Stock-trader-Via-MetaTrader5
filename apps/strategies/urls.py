from django.urls import path

from apps.strategies.views import (
    CustomStrategyCreateView,
    LibrarySeedVariantView,
    StrategyDuplicateView,
    StrategyListView,
    StrategyParametersView,
)

app_name = "strategies"

urlpatterns = [
    path("", StrategyListView.as_view(), name="list"),
    path("custom/new/", CustomStrategyCreateView.as_view(), name="custom_create"),
    path("<int:pk>/parameters/", StrategyParametersView.as_view(), name="parameters"),
    path("<int:pk>/duplicate/", StrategyDuplicateView.as_view(), name="duplicate"),
    path("library/<slug:slug>/configure/", LibrarySeedVariantView.as_view(), name="library_configure"),
]
