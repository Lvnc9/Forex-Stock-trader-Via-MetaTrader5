import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, ListView

from apps.backtest.forms import BacktestRunForm
from apps.backtest.models import BacktestRun
from apps.backtest.tasks import enqueue_backtest


@method_decorator(login_required, name="dispatch")
class BacktestListView(ListView):
    model = BacktestRun
    template_name = "backtest/list.html"
    context_object_name = "runs"
    paginate_by = 20


@method_decorator(login_required, name="dispatch")
class BacktestCreateView(CreateView):
    model = BacktestRun
    form_class = BacktestRunForm
    template_name = "backtest/form.html"
    success_url = reverse_lazy("backtest:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["data_root"] = settings.TRADEBOT_DATA_ROOT
        return kwargs

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.status = BacktestRun.Status.PENDING
        self.object.save()
        enqueue_backtest(self.object)
        return redirect("backtest:detail", pk=self.object.pk)


@method_decorator(login_required, name="dispatch")
class BacktestDetailView(DetailView):
    model = BacktestRun
    template_name = "backtest/detail.html"
    context_object_name = "run"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        run = self.object
        curve = run.equity_curve or []
        if len(curve) > 500:
            step = max(len(curve) // 500, 1)
            curve = curve[::step]
        ctx["equity_chart_json"] = json.dumps(curve)
        ctx["metrics"] = run.metrics or {}
        ctx["trade_rows"] = run.trades or []
        return ctx
