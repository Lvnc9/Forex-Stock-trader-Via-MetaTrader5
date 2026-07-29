from django import forms

from apps.backtest.models import BacktestRun
from apps.brokers.models import TradingAgent
from apps.marketdata.catalog import scan_data_root
from apps.marketdata.models import SymbolMap
from apps.strategies.models import Strategy
from apps.trading.models import Deployment


class DeploymentDraftForm(forms.ModelForm):
    class Meta:
        model = Deployment
        fields = ["strategy", "agent", "catalog_slug", "mt5_symbol", "timeframe", "lot_size", "notes"]
        widgets = {
            "strategy": forms.Select(attrs={"class": "tb-input"}),
            "agent": forms.Select(attrs={"class": "tb-input"}),
            "catalog_slug": forms.Select(attrs={"class": "tb-input"}),
            "mt5_symbol": forms.TextInput(attrs={"class": "tb-input"}),
            "timeframe": forms.Select(attrs={"class": "tb-input"}),
            "lot_size": forms.NumberInput(attrs={"class": "tb-input", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "tb-input", "rows": 2}),
        }

    def __init__(self, *args, data_root=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["strategy"].queryset = Strategy.objects.all()
        self.fields["agent"].queryset = TradingAgent.objects.all()
        self.fields["mt5_symbol"].required = False
        slugs = [c.slug for c in scan_data_root(data_root)] if data_root else []
        self.fields["catalog_slug"] = forms.ChoiceField(
            choices=[(s, s) for s in slugs] or [("", "—")],
            widget=forms.Select(attrs={"class": "tb-input"}),
        )
        self.fields["timeframe"] = forms.ChoiceField(
            choices=[("M1", "M1"), ("M5", "M5"), ("M15", "M15"), ("H1", "H1")],
            initial="M5",
            widget=forms.Select(attrs={"class": "tb-input"}),
        )

    def clean(self):
        cleaned = super().clean()
        slug = cleaned.get("catalog_slug")
        symbol = (cleaned.get("mt5_symbol") or "").strip()
        if slug:
            sym_map = SymbolMap.objects.filter(catalog_slug=slug).first()
            if not sym_map or not (sym_map.mt5_symbol or "").strip():
                if not symbol:
                    self.add_error(
                        "mt5_symbol",
                        "Create a Symbol map for this catalog slug (Data → Symbol maps) "
                        "or enter the MT5 symbol manually.",
                    )
            elif not symbol:
                cleaned["mt5_symbol"] = sym_map.mt5_symbol.strip()
            else:
                cleaned["mt5_symbol"] = symbol
        return cleaned


class DeployConfirmForm(forms.Form):
    acknowledge = forms.BooleanField(
        required=False,
        label="I understand this will arm the deployment for the Windows agent to execute.",
    )
    live_confirm = forms.BooleanField(
        required=False,
        label="This is a LIVE account — I accept the risk of real-money trading.",
    )

    def __init__(self, *args, requires_live_confirm=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.requires_live_confirm = requires_live_confirm
        if requires_live_confirm:
            self.fields["live_confirm"].required = True
        self.fields["acknowledge"].required = True


def last_backtest_for(strategy: Strategy, catalog_slug: str) -> BacktestRun | None:
    return (
        BacktestRun.objects.filter(
            strategy=strategy,
            catalog_slug=catalog_slug,
            status=BacktestRun.Status.COMPLETED,
        )
        .order_by("-completed_at")
        .first()
    )
