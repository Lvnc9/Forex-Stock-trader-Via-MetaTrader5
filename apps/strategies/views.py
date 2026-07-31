import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.generic import ListView, View

from apps.strategies.forms import CustomStrategyForm
from apps.strategies.forms_builder import build_parameter_form_class
from apps.strategies.loader import load_strategy_class
from apps.strategies.models import Strategy
from apps.strategies.registry import LIBRARY_BY_SLUG, LIBRARY_STRATEGIES
from apps.strategies.rules.builder import RuleBuilderForm, initial_from_spec
from apps.strategies.rules.expr import ExprError
from apps.strategies.rules.runtime import RuleStrategy
from apps.strategies.rules.templates import get_template, list_templates
from apps.strategies.validation import (
    dry_run_rule_spec,
    install_custom_strategy_source,
    update_custom_strategy_source,
)


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
        ctx["rule_templates"] = list_templates()
        return ctx


@method_decorator(login_required, name="dispatch")
class StrategyParametersView(View):
    template_name = "strategies/parameters.html"

    def get(self, request, pk):
        strategy = get_object_or_404(Strategy, pk=pk)
        if strategy.is_rule_strategy:
            return redirect("strategies:rule_edit", pk=strategy.pk)
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
        if strategy.is_rule_strategy:
            return redirect("strategies:rule_edit", pk=strategy.pk)
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
            rule_spec=dict(original.rule_spec or {}),
            is_library=original.is_library,
            slug=new_slug,
            source_code=original.source_code,
        )
        messages.success(request, f"Duplicated as {clone.name}.")
        if clone.is_rule_strategy:
            return redirect("strategies:rule_edit", pk=clone.pk)
        return redirect("strategies:parameters", pk=clone.pk)


@method_decorator(login_required, name="dispatch")
class StrategyDeleteView(View):
    template_name = "strategies/confirm_delete.html"

    def get(self, request, pk):
        strategy = get_object_or_404(Strategy, pk=pk)
        return render(request, self.template_name, {"strategy": strategy})

    def post(self, request, pk):
        strategy = get_object_or_404(Strategy, pk=pk)
        if strategy.backtest_runs.exists() or strategy.deployments.exists():
            messages.error(
                request,
                "Cannot delete: this strategy has backtest runs or deployments. "
                "Archive by leaving it unused, or delete those records first.",
            )
            return redirect("strategies:list")
        name = strategy.name
        strategy.delete()
        messages.success(request, f"Deleted {name}.")
        return redirect("strategies:list")


@method_decorator(login_required, name="dispatch")
class CustomStrategyCreateView(View):
    template_name = "strategies/custom_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CustomStrategyForm(), "editing": False})

    def post(self, request):
        form = CustomStrategyForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "editing": False})

        try:
            module_path = install_custom_strategy_source(form.cleaned_data["source_code"])
        except Exception as exc:
            form.add_error("source_code", str(exc))
            return render(request, self.template_name, {"form": form, "editing": False})

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
class CustomStrategyEditView(View):
    template_name = "strategies/custom_form.html"

    def get(self, request, pk):
        strategy = get_object_or_404(Strategy, pk=pk)
        if not strategy.is_custom_python:
            messages.error(request, "Not a custom Python strategy.")
            return redirect("strategies:list")
        form = CustomStrategyForm(
            initial={
                "name": strategy.name,
                "description": strategy.description,
                "source_code": strategy.source_code,
            }
        )
        return render(request, self.template_name, {"form": form, "editing": True, "strategy": strategy})

    def post(self, request, pk):
        strategy = get_object_or_404(Strategy, pk=pk)
        if not strategy.is_custom_python:
            messages.error(request, "Not a custom Python strategy.")
            return redirect("strategies:list")
        form = CustomStrategyForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "editing": True, "strategy": strategy})

        try:
            update_custom_strategy_source(strategy.module_path, form.cleaned_data["source_code"])
        except Exception as exc:
            form.add_error("source_code", str(exc))
            return render(request, self.template_name, {"form": form, "editing": True, "strategy": strategy})

        strategy.name = form.cleaned_data["name"]
        strategy.description = form.cleaned_data.get("description") or ""
        strategy.source_code = form.cleaned_data["source_code"]
        strategy.save(update_fields=["name", "description", "source_code", "updated_at"])
        messages.success(request, "Custom strategy updated.")
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


@method_decorator(login_required, name="dispatch")
class RuleStrategyBuilderView(View):
    template_name = "strategies/rule_builder.html"

    def get(self, request, pk=None):
        strategy = get_object_or_404(Strategy, pk=pk) if pk else None
        from_slug = request.GET.get("from") or ""
        initial = {"name": "", "description": ""}
        template_meta = None

        if strategy and strategy.rule_spec:
            initial = initial_from_spec(
                strategy.rule_spec,
                name=strategy.name,
                description=strategy.description,
            )
        elif from_slug:
            template_meta = get_template(from_slug)
            if template_meta:
                initial = initial_from_spec(
                    template_meta["spec"],
                    name=template_meta["name"],
                    description=template_meta["description"],
                )
            else:
                messages.error(request, f"Unknown rule template: {from_slug}")

        form = RuleBuilderForm(initial=initial)
        return render(
            request,
            self.template_name,
            self._context(form, strategy, template_meta=template_meta),
        )

    def post(self, request, pk=None):
        strategy = get_object_or_404(Strategy, pk=pk) if pk else None
        form = RuleBuilderForm(request.POST)
        context = self._context(form, strategy)
        if not form.is_valid():
            return render(request, self.template_name, context)

        try:
            spec = form.build_spec()
            dry_run_rule_spec(spec)
        except (ExprError, Exception) as exc:
            form.add_error(None, str(exc))
            return render(request, self.template_name, context)

        defaults = {p["name"]: p.get("default", 0) for p in spec["parameters"]}
        name = form.cleaned_data["name"]
        description = form.cleaned_data.get("description") or ""

        if strategy:
            strategy.name = name
            strategy.description = description
            strategy.rule_spec = spec
            strategy.parameters = defaults
            strategy.module_path = RuleStrategy.module_path
            strategy.is_library = False
            strategy.save()
            messages.success(request, "Rule strategy updated.")
            return redirect("strategies:list")

        slug = slugify(name)[:50] or f"rule-{uuid.uuid4().hex[:8]}"
        if Strategy.objects.filter(slug=slug).exists():
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"
        Strategy.objects.create(
            name=name,
            description=description,
            module_path=RuleStrategy.module_path,
            parameters=defaults,
            rule_spec=spec,
            is_library=False,
            slug=slug,
        )
        messages.success(request, "Rule strategy created.")
        return redirect("strategies:list")

    @staticmethod
    def _expr_side(form, prefix: str) -> dict:
        return {
            "ref": form[f"{prefix}_ref"],
            "indicator": form[f"{prefix}_indicator"],
            "price": form[f"{prefix}_price"],
            "value": form[f"{prefix}_value"],
            "param": form[f"{prefix}_param"],
            "po_base_ref": form[f"{prefix}_po_base_ref"],
            "po_base_indicator": form[f"{prefix}_po_base_indicator"],
            "po_base_price": form[f"{prefix}_po_base_price"],
            "po_base_value": form[f"{prefix}_po_base_value"],
            "po_base_param": form[f"{prefix}_po_base_param"],
            "po_pct_ref": form[f"{prefix}_po_pct_ref"],
            "po_pct_value": form[f"{prefix}_po_pct_value"],
            "po_pct_param": form[f"{prefix}_po_pct_param"],
            "ar_op": form[f"{prefix}_ar_op"],
            "ar_left_ref": form[f"{prefix}_ar_left_ref"],
            "ar_left_indicator": form[f"{prefix}_ar_left_indicator"],
            "ar_left_price": form[f"{prefix}_ar_left_price"],
            "ar_left_value": form[f"{prefix}_ar_left_value"],
            "ar_left_param": form[f"{prefix}_ar_left_param"],
            "ar_right_ref": form[f"{prefix}_ar_right_ref"],
            "ar_right_indicator": form[f"{prefix}_ar_right_indicator"],
            "ar_right_price": form[f"{prefix}_ar_right_price"],
            "ar_right_value": form[f"{prefix}_ar_right_value"],
            "ar_right_param": form[f"{prefix}_ar_right_param"],
        }

    @classmethod
    def _context(cls, form, strategy, template_meta=None):
        param_rows = []
        for i in range(4):
            param_rows.append(
                {
                    "name": form[f"param_{i}_name"],
                    "type": form[f"param_{i}_type"],
                    "default": form[f"param_{i}_default"],
                    "min": form[f"param_{i}_min"],
                    "max": form[f"param_{i}_max"],
                }
            )
        ind_rows = []
        for i in range(6):
            ind_rows.append(
                {
                    "id": form[f"ind_{i}_id"],
                    "fn": form[f"ind_{i}_fn"],
                    "source": form[f"ind_{i}_source"],
                    "period": form[f"ind_{i}_period"],
                    "period_param": form[f"ind_{i}_period_param"],
                    "column": form[f"ind_{i}_column"],
                }
            )
        group_rows = []
        for key, label in (
            ("entry_long", "Entry long"),
            ("entry_short", "Entry short"),
            ("exit_long", "Exit long"),
            ("exit_short", "Exit short"),
        ):
            rules = []
            for i in range(4):
                prefix = f"{key}_{i}"
                rules.append(
                    {
                        "op": form[f"{prefix}_op"],
                        "left": cls._expr_side(form, f"{prefix}_left"),
                        "right": cls._expr_side(form, f"{prefix}_right"),
                    }
                )
            group_rows.append({"key": key, "label": label, "logic": form[f"{key}_logic"], "rules": rules})

        return {
            "form": form,
            "strategy": strategy,
            "param_rows": param_rows,
            "ind_rows": ind_rows,
            "group_rows": group_rows,
            "template_meta": template_meta,
        }
