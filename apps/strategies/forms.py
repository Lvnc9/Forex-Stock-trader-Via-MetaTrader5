from __future__ import annotations

from django import forms

from apps.strategies.validation import check_custom_strategy_source


class CustomStrategyForm(forms.Form):
    name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "tb-input"}))
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "tb-input", "rows": 3}),
    )
    source_code = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "tb-input font-mono text-xs",
                "rows": 18,
                "placeholder": "class MyStrategy(BaseStrategy):\n    ...",
            }
        ),
        help_text="Must subclass BaseStrategy and implement on_bar(). Validated with import + dry-run.",
    )

    def clean_source_code(self):
        source = self.cleaned_data["source_code"]
        check_custom_strategy_source(source)
        return source
