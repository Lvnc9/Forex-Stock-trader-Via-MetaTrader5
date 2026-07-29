from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView

from apps.brokers.forms import CreateAgentForm
from apps.brokers.models import TradingAgent
from apps.brokers.tokens import generate_agent_token, hash_agent_token
from apps.marketdata.models import SymbolMap


@method_decorator(login_required, name="dispatch")
class BrokerAgentsView(ListView):
    model = TradingAgent
    template_name = "brokers/agents.html"
    context_object_name = "agents"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["symbol_maps"] = SymbolMap.objects.all()
        ctx["create_form"] = CreateAgentForm()
        ctx["new_token"] = self.request.session.pop("new_agent_token", None)
        ctx["new_agent_name"] = self.request.session.pop("new_agent_name", None)
        return ctx


@method_decorator(login_required, name="dispatch")
class BrokerCreateAgentView(View):
    def post(self, request):
        form = CreateAgentForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Could not create agent.")
            return redirect("brokers:agents")

        plain_token = generate_agent_token()
        agent = form.save(commit=False)
        agent.token_hash = hash_agent_token(plain_token)
        agent.save()

        request.session["new_agent_token"] = plain_token
        request.session["new_agent_name"] = agent.name
        messages.success(request, f"Agent “{agent.name}” created. Copy the token now — it won't be shown again.")
        return redirect("brokers:agents")


@method_decorator(login_required, name="dispatch")
class BrokerAgentDeleteView(View):
    def post(self, request, pk):
        agent = get_object_or_404(TradingAgent, pk=pk)
        name = agent.name
        agent.delete()
        messages.success(request, f"Removed agent {name}.")
        return redirect("brokers:agents")
