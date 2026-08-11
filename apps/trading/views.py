from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView

from apps.brokers.models import TradingAgent
from apps.trading.forms import DeployConfirmForm, DeploymentDraftForm, last_backtest_for
from apps.trading.models import Deployment


@method_decorator(login_required, name="dispatch")
class DeploymentListView(ListView):
    model = Deployment
    template_name = "trading/deployments.html"
    context_object_name = "deployments"

    def get_queryset(self):
        return Deployment.objects.select_related("strategy", "agent").prefetch_related("events")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["agent_feeds"] = []
        for agent in TradingAgent.objects.all():
            sync = agent.sync_snapshot or {}
            ctx["agent_feeds"].append(
                {
                    "agent": agent,
                    "positions": sync.get("positions", []),
                    "deals": sync.get("deals", [])[:15],
                    "errors": sync.get("errors", [])[:8],
                }
            )
        return ctx


@method_decorator(login_required, name="dispatch")
class DeploymentCreateView(View):
    template_name = "trading/deploy_form.html"

    def get(self, request):
        form = DeploymentDraftForm(data_root=settings.TRADEBOT_DATA_ROOT)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = DeploymentDraftForm(request.POST, data_root=settings.TRADEBOT_DATA_ROOT)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        deployment = form.save(commit=False)
        deployment.status = Deployment.Status.DRAFT
        deployment.parameters = dict(deployment.strategy.runtime_parameters())
        deployment.save()
        return redirect("trading:review", pk=deployment.pk)


@method_decorator(login_required, name="dispatch")
class DeploymentReviewView(View):
    template_name = "trading/deploy_review.html"

    def get(self, request, pk):
        deployment = get_object_or_404(Deployment, pk=pk)
        requires_live = deployment.agent.is_live_account
        form = DeployConfirmForm(requires_live_confirm=requires_live)
        last_bt = last_backtest_for(deployment.strategy, deployment.catalog_slug)
        return render(
            request,
            self.template_name,
            {
                "deployment": deployment,
                "form": form,
                "last_backtest": last_bt,
                "requires_live": requires_live,
            },
        )

    def post(self, request, pk):
        deployment = get_object_or_404(Deployment, pk=pk)
        requires_live = deployment.agent.is_live_account
        form = DeployConfirmForm(request.POST, requires_live_confirm=requires_live)
        if not form.is_valid():
            last_bt = last_backtest_for(deployment.strategy, deployment.catalog_slug)
            return render(
                request,
                self.template_name,
                {
                    "deployment": deployment,
                    "form": form,
                    "last_backtest": last_bt,
                    "requires_live": requires_live,
                },
            )

        deployment.status = Deployment.Status.ARMED
        deployment.live_confirmed = bool(form.cleaned_data.get("live_confirm"))
        if requires_live and not deployment.live_confirmed:
            messages.error(request, "Live account confirmation is required.")
            return redirect("trading:review", pk=deployment.pk)
        deployment.save(update_fields=["status", "live_confirmed", "updated_at"])
        from apps.trading.events import record_event

        record_event(
            deployment,
            "armed",
            "Deployment armed for agent poll.",
            {"live_confirmed": deployment.live_confirmed},
        )
        messages.success(request, "Deployment armed. The agent will pick it up on the next poll.")
        return redirect("trading:list")


@method_decorator(login_required, name="dispatch")
class DeploymentPauseView(View):
    def post(self, request, pk):
        deployment = get_object_or_404(Deployment, pk=pk)
        deployment.status = Deployment.Status.PAUSED
        deployment.save(update_fields=["status", "updated_at"])
        from apps.trading.events import record_event

        record_event(deployment, "paused", "Paused by user.")
        return redirect("trading:list")


@method_decorator(login_required, name="dispatch")
class DeploymentRearmView(View):
    def post(self, request, pk):
        deployment = get_object_or_404(Deployment, pk=pk)
        if deployment.status != Deployment.Status.PAUSED:
            messages.warning(request, "Only paused deployments can be re-armed via review.")
            return redirect("trading:list")
        deployment.status = Deployment.Status.DRAFT
        deployment.save(update_fields=["status", "updated_at"])
        from apps.trading.events import record_event

        record_event(deployment, "draft", "Returned to draft for re-review.")
        return redirect("trading:review", pk=deployment.pk)


@method_decorator(login_required, name="dispatch")
class DeploymentStopView(View):
    def post(self, request, pk):
        deployment = get_object_or_404(Deployment, pk=pk)
        deployment.status = Deployment.Status.STOPPED
        deployment.save(update_fields=["status", "updated_at"])
        from apps.trading.events import record_event

        record_event(deployment, "stopped", "Stopped by user.")
        return redirect("trading:list")
