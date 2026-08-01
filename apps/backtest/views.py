import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView

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
        self.object.progress_pct = 0.0
        self.object.progress_message = "Queued"
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


@method_decorator(login_required, name="dispatch")
class BacktestStatusView(View):
    """Lightweight JSON status for HTMX / polling (keeps detail page snappy)."""

    def get(self, request, pk: int):
        run = get_object_or_404(BacktestRun, pk=pk)
        return JsonResponse(
            {
                "id": run.pk,
                "status": run.status,
                "progress_pct": run.progress_pct,
                "progress_message": run.progress_message,
                "error_message": run.error_message,
                "win_rate_pct": run.win_rate_pct,
                "done": run.status
                in (BacktestRun.Status.COMPLETED, BacktestRun.Status.FAILED),
            }
        )


@method_decorator(login_required, name="dispatch")
class BacktestCompareView(TemplateView):
    template_name = "backtest/compare.html"

    def get(self, request, *args, **kwargs):
        raw_ids = request.GET.getlist("ids")
        try:
            ids = [int(x) for x in raw_ids[:4]]
        except ValueError:
            ids = []
        if len(ids) < 2:
            messages.warning(request, "Select at least two completed runs to compare.")
            return redirect("backtest:list")
        runs = list(BacktestRun.objects.filter(pk__in=ids, status=BacktestRun.Status.COMPLETED))
        if len(runs) < 2:
            messages.warning(request, "Need at least two completed runs in your selection.")
            return redirect("backtest:list")
        self.compare_runs = sorted(runs, key=lambda r: r.created_at, reverse=True)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["runs"] = getattr(self, "compare_runs", [])
        return ctx
