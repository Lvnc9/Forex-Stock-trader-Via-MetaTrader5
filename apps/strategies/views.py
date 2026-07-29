from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from apps.strategies.models import Strategy
from apps.strategies.registry import LIBRARY_STRATEGIES


@method_decorator(login_required, name="dispatch")
class StrategyListView(ListView):
    model = Strategy
    template_name = "strategies/list.html"
    context_object_name = "strategies"

    def get_queryset(self):
        return Strategy.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["library_classes"] = LIBRARY_STRATEGIES
        return ctx
