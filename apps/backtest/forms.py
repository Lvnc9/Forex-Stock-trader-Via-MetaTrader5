from django import forms
from django.core.cache import cache

from apps.backtest.models import BacktestRun
from apps.marketdata.catalog import scan_data_root
from apps.marketdata.timeframes import (
    HTF_TIMEFRAME_CHOICES,
    TIMEFRAME_CHOICES,
    TIMEFRAME_LABELS,
    is_higher_timeframe,
    normalize_timeframe,
)
from apps.strategies.models import Strategy
from apps.strategies.rules.htf_gate import strategy_requires_htf


def _catalog_slug_choices(data_root) -> list[tuple[str, str]]:
    if data_root is None:
        return [("", "— no datasets —")]
    cache_key = f"backtest:catalog_slugs:{data_root}"
    slugs = cache.get(cache_key)
    if slugs is None:
        slugs = [c.slug for c in scan_data_root(data_root)]
        cache.set(cache_key, slugs, 120)
    return [(s, s) for s in slugs] or [("", "— no datasets —")]


class BacktestRunForm(forms.ModelForm):
    class Meta:
        model = BacktestRun
        fields = [
            "strategy",
            "catalog_slug",
            "timeframe",
            "htf_timeframe",
            "start",
            "end",
            "initial_balance",
            "spread_pct",
            "commission",
            "sizing_mode",
            "lot_size",
            "contract_size",
        ]
        widgets = {
            "start": forms.DateInput(attrs={"type": "date", "class": "tb-input"}),
            "end": forms.DateInput(attrs={"type": "date", "class": "tb-input"}),
            "strategy": forms.Select(attrs={"class": "tb-input"}),
            "catalog_slug": forms.Select(attrs={"class": "tb-input"}),
            "timeframe": forms.Select(attrs={"class": "tb-input"}),
            "htf_timeframe": forms.Select(attrs={"class": "tb-input"}),
            "initial_balance": forms.NumberInput(attrs={"class": "tb-input", "step": "0.01"}),
            "spread_pct": forms.NumberInput(attrs={"class": "tb-input", "step": "0.00001"}),
            "commission": forms.NumberInput(attrs={"class": "tb-input", "step": "0.01"}),
            "sizing_mode": forms.Select(attrs={"class": "tb-input"}),
            "lot_size": forms.NumberInput(attrs={"class": "tb-input", "step": "0.01"}),
            "contract_size": forms.NumberInput(attrs={"class": "tb-input", "step": "1"}),
        }
        labels = {
            "htf_timeframe": "Higher timeframe (optional)",
            "timeframe": "Primary timeframe",
            "sizing_mode": "Position sizing",
            "lot_size": "Lot size",
            "contract_size": "Contract size (units per lot)",
        }
        help_texts = {
            "timeframe": (
                "Bars are loaded as M1 OHLC from disk, then resampled to this timeframe "
                f"({', '.join(f'{k}={v}' for k, v in TIMEFRAME_LABELS.items())})."
            ),
            "htf_timeframe": (
                "Passed to strategies as ctx.htf_bars / ctx.htf_indicators. Leave blank if unused."
            ),
            "sizing_mode": (
                "All-in sizes each entry as cash ÷ price. Fixed lots uses lot_size × contract_size "
                "(same lot semantics as live Deployment.lot_size)."
            ),
            "lot_size": "Ignored for all-in. Default 0.01 matches live deployments.",
            "contract_size": "100000 = standard FX lot. Lower for some CFDs/indices.",
        }

    def __init__(self, *args, data_root=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["strategy"].queryset = Strategy.objects.all()
        self.fields["catalog_slug"] = forms.ChoiceField(
            choices=_catalog_slug_choices(data_root),
            widget=forms.Select(attrs={"class": "tb-input"}),
        )
        self.fields["timeframe"] = forms.ChoiceField(
            choices=TIMEFRAME_CHOICES,
            initial="M5",
            widget=forms.Select(attrs={"class": "tb-input"}),
            label="Primary timeframe",
            help_text=self.Meta.help_texts["timeframe"],
        )
        self.fields["htf_timeframe"] = forms.ChoiceField(
            choices=HTF_TIMEFRAME_CHOICES,
            required=False,
            initial="",
            widget=forms.Select(attrs={"class": "tb-input"}),
            label="Higher timeframe (optional)",
            help_text=self.Meta.help_texts["htf_timeframe"],
        )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start")
        end = cleaned.get("end")
        if start and end and end < start:
            raise forms.ValidationError("End date must be on or after start date.")

        primary = normalize_timeframe(cleaned.get("timeframe") or "")
        htf = normalize_timeframe(cleaned.get("htf_timeframe") or "")
        cleaned["htf_timeframe"] = htf
        if htf and primary and not is_higher_timeframe(htf, primary):
            self.add_error(
                "htf_timeframe",
                f"HTF must be higher than primary timeframe ({primary}).",
            )
        strategy = cleaned.get("strategy")
        if strategy_requires_htf(strategy) and not htf:
            self.add_error(
                "htf_timeframe",
                "This strategy uses HTF indicators — choose a higher timeframe.",
            )

        sizing_mode = cleaned.get("sizing_mode") or BacktestRun.SizingMode.ALL_IN
        lot_size = cleaned.get("lot_size")
        contract_size = cleaned.get("contract_size")
        if sizing_mode == BacktestRun.SizingMode.FIXED_LOTS:
            if lot_size is None or float(lot_size) <= 0:
                self.add_error("lot_size", "Lot size must be positive for fixed-lots sizing.")
            if contract_size is None or float(contract_size) <= 0:
                self.add_error("contract_size", "Contract size must be positive.")
        elif contract_size is not None and float(contract_size) <= 0:
            self.add_error("contract_size", "Contract size must be positive.")
        return cleaned
