from django.urls import path

from apps.strategies.views import (
    CustomStrategyCreateView,
    CustomStrategyEditView,
    LibrarySeedVariantView,
    RuleBuilderRowView,
    RuleStrategyBuilderView,
    StrategyDeleteView,
    StrategyDuplicateView,
    StrategyListView,
    StrategyParametersView,
)

app_name = "strategies"

urlpatterns = [
    path("", StrategyListView.as_view(), name="list"),
    path("custom/new/", CustomStrategyCreateView.as_view(), name="custom_create"),
    path("custom/<int:pk>/edit/", CustomStrategyEditView.as_view(), name="custom_edit"),
    path("rules/new/", RuleStrategyBuilderView.as_view(), name="rule_create"),
    path("rules/<int:pk>/edit/", RuleStrategyBuilderView.as_view(), name="rule_edit"),
    path("rules/row/<str:kind>/", RuleBuilderRowView.as_view(), name="builder_row"),
    path("<int:pk>/parameters/", StrategyParametersView.as_view(), name="parameters"),
    path("<int:pk>/duplicate/", StrategyDuplicateView.as_view(), name="duplicate"),
    path("<int:pk>/delete/", StrategyDeleteView.as_view(), name="delete"),
    path("library/<slug:slug>/configure/", LibrarySeedVariantView.as_view(), name="library_configure"),
]
