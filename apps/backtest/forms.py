from django import forms

from apps.backtest.models import BacktestRun
from apps.marketdata.catalog import scan_data_root
from apps.marketdata.timeframes import (
    HTF_TIMEFRAME_CHOICES,
    TIMEFRAME_CHOICES,
    is_higher_timeframe,
    normalize_timeframe,
)
from apps.strategies.models import Strategy


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
        }
        help_texts = {
            "htf_timeframe": "Passed to strategies as ctx.htf_bars / ctx.htf_indicators. Leave blank if unused.",
        }

    def __init__(self, *args, data_root=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["strategy"].queryset = Strategy.objects.all()
        slugs = []
        if data_root is not None:
            slugs = [c.slug for c in scan_data_root(data_root)]
        self.fields["catalog_slug"] = forms.ChoiceField(
            choices=[(s, s) for s in slugs] or [("", "— no datasets —")],
            widget=forms.Select(attrs={"class": "tb-input"}),
        )
        self.fields["timeframe"] = forms.ChoiceField(
            choices=TIMEFRAME_CHOICES,
            initial="M5",
            widget=forms.Select(attrs={"class": "tb-input"}),
        )
        self.fields["htf_timeframe"] = forms.ChoiceField(
            choices=HTF_TIMEFRAME_CHOICES,
            required=False,
            initial="",
            widget=forms.Select(attrs={"class": "tb-input"}),
            label="Higher timeframe (optional)",
            help_text="Passed to strategies as ctx.htf_bars / ctx.htf_indicators. Leave blank if unused.",
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
        return cleaned
