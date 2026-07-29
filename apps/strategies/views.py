import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.generic import ListView, View

from apps.strategies.forms import CustomStrategyForm
from apps.strategies.forms_builder import build_parameter_form_class
from apps.strategies.loader import load_strategy_class
from apps.strategies.models import Strategy
from apps.strategies.registry import LIBRARY_BY_SLUG, LIBRARY_STRATEGIES
from apps.strategies.validation import install_custom_strategy_source


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


@method_decorator(login_required, name="dispatch")
class StrategyParametersView(View):
    template_name = "strategies/parameters.html"

    def get(self, request, pk):
        strategy = get_object_or_404(Strategy, pk=pk)
        cls = load_strategy_class(strategy.module_path)
        form_class = build_parameter_form_class(cls)
        form = form_class(initial=strategy.parameters or cls.default_parameters)
        return render(
            request,
            self.template_name,
            {"strategy": strategy, "form": form, "schema": cls.parameter_schema},
        )

    def post(self, request, pk):
        strategy = get_object_or_404(Strategy, pk=pk)
        cls = load_strategy_class(strategy.module_path)
        form_class = build_parameter_form_class(cls)
        form = form_class(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"strategy": strategy, "form": form, "schema": cls.parameter_schema},
            )

        strategy.parameters = form.cleaned_data
        strategy.save(update_fields=["parameters", "updated_at"])
        messages.success(request, f"Saved parameters for {strategy.name}.")
        return redirect("strategies:list")


@method_decorator(login_required, name="dispatch")
class StrategyDuplicateView(View):
    def post(self, request, pk):
        original = get_object_or_404(Strategy, pk=pk)
        base_slug = slugify(original.slug or original.name)[:40]
        new_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        clone = Strategy.objects.create(
            name=f"{original.name} (copy)",
            description=original.description,
            module_path=original.module_path,
            parameters=dict(original.parameters or {}),
            is_library=original.is_library,
            slug=new_slug,
            source_code=original.source_code,
        )
        messages.success(request, f"Duplicated as {clone.name}.")
        return redirect("strategies:parameters", pk=clone.pk)


@method_decorator(login_required, name="dispatch")
class CustomStrategyCreateView(View):
    template_name = "strategies/custom_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CustomStrategyForm()})

    def post(self, request):
        form = CustomStrategyForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        try:
            module_path = install_custom_strategy_source(form.cleaned_data["source_code"])
        except Exception as exc:
            form.add_error("source_code", str(exc))
            return render(request, self.template_name, {"form": form})

        slug = slugify(form.cleaned_data["name"])[:50] or f"custom-{uuid.uuid4().hex[:8]}"
        if Strategy.objects.filter(slug=slug).exists():
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"

        Strategy.objects.create(
            name=form.cleaned_data["name"],
            description=form.cleaned_data.get("description") or "",
            module_path=module_path,
            parameters={},
            is_library=False,
            slug=slug,
            source_code=form.cleaned_data["source_code"],
        )
        messages.success(request, "Custom strategy saved and validated.")
        return redirect("strategies:list")


@method_decorator(login_required, name="dispatch")
class LibrarySeedVariantView(View):
    """Create a DB strategy row from a library class for parameter editing."""

    def post(self, request, slug):
        cls = LIBRARY_BY_SLUG.get(slug)
        if cls is None:
            messages.error(request, "Unknown library strategy.")
            return redirect("strategies:list")

        strategy, created = Strategy.objects.get_or_create(
            slug=cls.slug,
            defaults={
                "name": cls.name,
                "description": cls.description,
                "module_path": cls.module_path,
                "parameters": dict(cls.default_parameters),
                "is_library": True,
            },
        )
        return redirect("strategies:parameters", pk=strategy.pk)
