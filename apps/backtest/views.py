import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from apps.backtest.defaults import backtest_form_defaults
from apps.backtest.forms import BacktestRunForm, ParamSweepForm
from apps.backtest.models import BacktestRun
from apps.backtest.progress import fail_orphaned_runs
from apps.backtest.tasks import enqueue_backtest, enqueue_sweep
from apps.strategies.models import Strategy


def _strategy_edit_url(strategy: Strategy) -> str:
    if strategy.is_rule_strategy:
        return reverse("strategies:rule_edit", kwargs={"pk": strategy.pk})
    if strategy.is_custom_python:
        return reverse("strategies:custom_edit", kwargs={"pk": strategy.pk})
    return reverse("strategies:parameters", kwargs={"pk": strategy.pk})


@method_decorator(login_required, name="dispatch")
class BacktestListView(ListView):
    model = BacktestRun
    template_name = "backtest/list.html"
    context_object_name = "runs"
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        fail_orphaned_runs()
        return super().get(request, *args, **kwargs)


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

    def get_initial(self):
        initial = super().get_initial()
        strategy_pk = self.request.GET.get("strategy")
        if strategy_pk:
            try:
                strategy = Strategy.objects.get(pk=int(strategy_pk))
            except (ValueError, Strategy.DoesNotExist):
                pass
            else:
                initial["strategy"] = strategy.pk
        initial.setdefault("initial_balance", BacktestRun._meta.get_field("initial_balance").default)
        initial.setdefault("thermal_profile", BacktestRun.ThermalProfile.LAPTOP)
        initial.update(backtest_form_defaults(settings.TRADEBOT_DATA_ROOT))
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        strategy_pk = self.request.GET.get("strategy")
        if strategy_pk:
            try:
                ctx["prefill_strategy"] = Strategy.objects.get(pk=int(strategy_pk))
            except (ValueError, Strategy.DoesNotExist):
                pass
        return ctx

    def form_valid(self, form):
        fail_orphaned_runs()
        self.object = form.save(commit=False)
        self.object.status = BacktestRun.Status.PENDING
        self.object.progress_pct = 0.0
        self.object.progress_message = "Queued"
        self.object.save()
        enqueue_backtest(self.object)
        return redirect("backtest:detail", pk=self.object.pk)


@method_decorator(login_required, name="dispatch")
class BacktestSweepCreateView(CreateView):
    """Enqueue a small parameter sweep; each value becomes an independent BacktestRun."""

    model = BacktestRun
    form_class = ParamSweepForm
    template_name = "backtest/sweep_form.html"
    success_url = reverse_lazy("backtest:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["data_root"] = settings.TRADEBOT_DATA_ROOT
        return kwargs

    def form_valid(self, form):
        overrides_list = form.cleaned_data["override_dicts"]
        base = form.save(commit=False)
        runs: list[BacktestRun] = []
        for overrides in overrides_list:
            run = BacktestRun(
                strategy=base.strategy,
                catalog_slug=base.catalog_slug,
                timeframe=base.timeframe,
                htf_timeframe=base.htf_timeframe or "",
                start=base.start,
                end=base.end,
                initial_balance=base.initial_balance,
                spread_pct=base.spread_pct,
                commission=base.commission,
                sizing_mode=base.sizing_mode,
                lot_size=base.lot_size,
                contract_size=base.contract_size,
                thermal_profile=base.thermal_profile or BacktestRun.ThermalProfile.LAPTOP,
                parameter_overrides=overrides,
                status=BacktestRun.Status.PENDING,
                progress_pct=0.0,
                progress_message="Queued (sweep)",
            )
            run.save()
            runs.append(run)
        enqueue_sweep(runs)
        messages.success(
            self.request,
            f"Queued {len(runs)}-run parameter sweep "
            f"({form.cleaned_data['param_name']}={form.cleaned_data['parsed_values']}).",
        )
        return redirect("backtest:list")


@method_decorator(login_required, name="dispatch")
class BacktestDetailView(DetailView):
    model = BacktestRun
    template_name = "backtest/detail.html"
    context_object_name = "run"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        run = self.object
        metrics = run.metrics or {}
        curve = run.equity_curve or []
        if len(curve) > 500:
            step = max(len(curve) // 500, 1)
            curve = curve[::step]
            if curve[-1] is not run.equity_curve[-1]:
                curve.append(run.equity_curve[-1])
        ctx["equity_chart_json"] = json.dumps(curve)
        ctx["metrics"] = metrics
        ctx["trade_rows"] = run.trades or []
        ctx["final_balance"] = metrics.get("final_balance")
        try:
            ctx["balance_up"] = float(ctx["final_balance"]) >= float(run.initial_balance)
        except (TypeError, ValueError):
            ctx["balance_up"] = True
        ctx["strategy_params"] = dict(run.strategy.parameters or {})
        ctx["strategy_edit_url"] = _strategy_edit_url(run.strategy)
        ctx["celery_eager"] = bool(getattr(settings, "CELERY_TASK_ALWAYS_EAGER", True))
        ctx["thermal_profile_label"] = run.get_thermal_profile_display()
        ctx["is_in_progress"] = run.status in (
            BacktestRun.Status.PENDING,
            BacktestRun.Status.RUNNING,
        )
        ctx["can_delete"] = run.status in (
            BacktestRun.Status.COMPLETED,
            BacktestRun.Status.FAILED,
        )
        ctx["current_balance"] = metrics.get("final_balance")
        return ctx


@method_decorator(login_required, name="dispatch")
class BacktestStatusView(View):
    """Lightweight JSON status for HTMX / polling (keeps detail page snappy)."""

    def get(self, request, pk: int):
        run = get_object_or_404(BacktestRun, pk=pk)
        metrics = dict(run.metrics or {})
        open_position = metrics.pop("open_position", None)
        current_balance = metrics.get("final_balance")
        trades = run.trades or []
        return JsonResponse(
            {
                "id": run.pk,
                "status": run.status,
                "progress_pct": run.progress_pct,
                "progress_message": run.progress_message,
                "error_message": run.error_message,
                "win_rate_pct": metrics.get("win_rate_pct"),
                "initial_balance": float(run.initial_balance),
                "current_balance": current_balance,
                "final_balance": metrics.get("final_balance"),
                "metrics": metrics,
                "trades": trades,
                "trade_count": len(trades),
                "open_position": open_position,
                "done": run.status
                in (BacktestRun.Status.COMPLETED, BacktestRun.Status.FAILED),
            }
        )


@method_decorator(login_required, name="dispatch")
class BacktestDeleteView(View):
    def post(self, request, pk: int):
        run = get_object_or_404(BacktestRun, pk=pk)
        if run.status in (BacktestRun.Status.PENDING, BacktestRun.Status.RUNNING):
            messages.error(
                request,
                "Cannot delete a backtest while it is still running. "
                "Wait for completion or let orphan cleanup fail stuck runs.",
            )
            return redirect("backtest:list")
        label = f"{run.strategy.name} · {run.catalog_slug}"
        run.delete()
        messages.success(request, f"Deleted backtest {label}.")
        return redirect("backtest:list")


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
