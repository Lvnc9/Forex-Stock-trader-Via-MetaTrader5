from __future__ import annotations

from django import forms


def build_parameter_form_class(strategy_class: type):
    fields: dict = {}
    for spec in strategy_class.parameter_schema:
        name = spec["name"]
        field_type = spec.get("type", "float")
        default = spec.get("default", strategy_class.default_parameters.get(name))
        widget_attrs = {"class": "tb-input"}
        if field_type == "int":
            fields[name] = forms.IntegerField(
                min_value=spec.get("min"),
                max_value=spec.get("max"),
                initial=default,
                required=True,
                widget=forms.NumberInput(attrs=widget_attrs),
            )
        else:
            fields[name] = forms.FloatField(
                min_value=spec.get("min"),
                max_value=spec.get("max"),
                initial=default,
                required=True,
                widget=forms.NumberInput(attrs={**widget_attrs, "step": "any"}),
            )

    return type(f"{strategy_class.__name__}ParamsForm", (forms.Form,), fields)
