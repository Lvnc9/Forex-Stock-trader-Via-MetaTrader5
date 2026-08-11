from django import forms

from apps.marketdata.models import SymbolMap


class SymbolMapForm(forms.ModelForm):
    class Meta:
        model = SymbolMap
        fields = ["catalog_slug", "dukascopy_id", "mt5_symbol", "notes"]
        widgets = {
            "catalog_slug": forms.TextInput(attrs={"class": "tb-input"}),
            "dukascopy_id": forms.TextInput(attrs={"class": "tb-input"}),
            "mt5_symbol": forms.TextInput(attrs={"class": "tb-input"}),
            "notes": forms.TextInput(attrs={"class": "tb-input"}),
        }

    def clean_mt5_symbol(self):
        value = (self.cleaned_data.get("mt5_symbol") or "").strip()
        if not value:
            raise forms.ValidationError("MT5 symbol is required.")
        return value
