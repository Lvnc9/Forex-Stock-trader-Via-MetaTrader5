from django import forms

from apps.backtest.models import BacktestRun
from apps.marketdata.catalog import scan_data_root
from apps.strategies.models import Strategy


class BacktestRunForm(forms.ModelForm):
    class Meta:
        model = BacktestRun
        fields = [
            "strategy",
            "catalog_slug",
            "timeframe",
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
            "initial_balance": forms.NumberInput(attrs={"class": "tb-input", "step": "0.01"}),
            "spread_pct": forms.NumberInput(attrs={"class": "tb-input", "step": "0.00001"}),
            "commission": forms.NumberInput(attrs={"class": "tb-input", "step": "0.01"}),
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
            choices=[
                ("M1", "M1"),
                ("M5", "M5"),
                ("M15", "M15"),
                ("M30", "M30"),
                ("H1", "H1"),
                ("H4", "H4"),
                ("D1", "D1"),
            ],
            initial="M5",
            widget=forms.Select(attrs={"class": "tb-input"}),
        )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start")
        end = cleaned.get("end")
        if start and end and end < start:
            raise forms.ValidationError("End date must be on or after start date.")
        return cleaned
