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
        }
        labels = {
            "htf_timeframe": "Higher timeframe (optional)",
            "timeframe": "Primary timeframe",
        }
        help_texts = {
            "timeframe": (
                "Bars are loaded as M1 OHLC from disk, then resampled to this timeframe "
                f"({', '.join(f'{k}={v}' for k, v in TIMEFRAME_LABELS.items())})."
            ),
            "htf_timeframe": (
                "Passed to strategies as ctx.htf_bars / ctx.htf_indicators. Leave blank if unused."
            ),
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
        return cleaned
