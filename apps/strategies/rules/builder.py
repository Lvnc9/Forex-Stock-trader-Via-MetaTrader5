"""Parse fixed-slot rule builder POST data into a validated rule_spec."""

from __future__ import annotations

from typing import Any

from django import forms

from apps.strategies.rules.expr import ARITH_OPS, COMPARE_OPS, INDICATOR_FNS, ExprError
from apps.strategies.rules.schema import empty_spec, validate_spec

MAX_PARAMS = 4
MAX_INDICATORS = 6
MAX_RULES = 4

SIMPLE_REFS = frozenset({"indicator", "price", "value", "param"})
REF_CHOICES = [
    ("", "—"),
    ("indicator", "Indicator"),
    ("price", "Price"),
    ("value", "Value"),
    ("param", "Param"),
    ("pct_offset", "Pct offset"),
    ("arith", "Arithmetic"),
]
NESTED_REF_CHOICES = [
    ("", "—"),
    ("indicator", "Indicator"),
    ("price", "Price"),
    ("value", "Value"),
    ("param", "Param"),
]

OP_CHOICES = [("", "—")] + [(op, op) for op in sorted(COMPARE_OPS)]
FN_CHOICES = [("", "—")] + [(fn, fn) for fn in sorted(INDICATOR_FNS)]
PRICE_CHOICES = [("", "—"), ("open", "open"), ("high", "high"), ("low", "low"), ("close", "close")]
LOGIC_CHOICES = [("and", "AND"), ("or", "OR")]
ARITH_CHOICES = [("", "—")] + [(op, op) for op in sorted(ARITH_OPS)]
SOURCE_CHOICES = [("primary", "Primary"), ("htf", "HTF")]


class RuleBuilderForm(forms.Form):
    name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "tb-input"}))
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "tb-input", "rows": 2}),
    )

    stop_type = forms.ChoiceField(
        choices=[("", "None"), ("pct", "Percent"), ("atr", "ATR")],
        required=False,
        widget=forms.Select(attrs={"class": "tb-input"}),
    )
    stop_pct = forms.FloatField(required=False, min_value=0.01, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))
    stop_atr_mult = forms.FloatField(required=False, min_value=0.1, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))
    stop_atr_period = forms.IntegerField(required=False, min_value=2, widget=forms.NumberInput(attrs={"class": "tb-input"}))

    tp_type = forms.ChoiceField(
        choices=[("", "None"), ("pct", "Percent"), ("rr", "Risk:Reward")],
        required=False,
        widget=forms.Select(attrs={"class": "tb-input"}),
    )
    tp_pct = forms.FloatField(required=False, min_value=0.01, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))
    tp_rr = forms.FloatField(required=False, min_value=0.1, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(MAX_PARAMS):
            self.fields[f"param_{i}_name"] = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"class": "tb-input"}))
            self.fields[f"param_{i}_type"] = forms.ChoiceField(
                choices=[("int", "int"), ("float", "float")],
                required=False,
                initial="float",
                widget=forms.Select(attrs={"class": "tb-input"}),
            )
            self.fields[f"param_{i}_default"] = forms.FloatField(required=False, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))
            self.fields[f"param_{i}_min"] = forms.FloatField(required=False, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))
            self.fields[f"param_{i}_max"] = forms.FloatField(required=False, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))

        for i in range(MAX_INDICATORS):
            self.fields[f"ind_{i}_id"] = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"class": "tb-input"}))
            self.fields[f"ind_{i}_fn"] = forms.ChoiceField(choices=FN_CHOICES, required=False, widget=forms.Select(attrs={"class": "tb-input"}))
            self.fields[f"ind_{i}_source"] = forms.ChoiceField(
                choices=SOURCE_CHOICES,
                required=False,
                initial="primary",
                widget=forms.Select(attrs={"class": "tb-input"}),
            )
            self.fields[f"ind_{i}_period"] = forms.IntegerField(required=False, min_value=1, widget=forms.NumberInput(attrs={"class": "tb-input"}))
            self.fields[f"ind_{i}_period_param"] = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"class": "tb-input"}))
            self.fields[f"ind_{i}_column"] = forms.ChoiceField(choices=PRICE_CHOICES, required=False, initial="close", widget=forms.Select(attrs={"class": "tb-input"}))

        for group in ("entry_long", "entry_short", "exit_long", "exit_short"):
            self.fields[f"{group}_logic"] = forms.ChoiceField(
                choices=LOGIC_CHOICES,
                required=False,
                initial="and",
                widget=forms.Select(attrs={"class": "tb-input"}),
            )
            for i in range(MAX_RULES):
                prefix = f"{group}_{i}"
                self.fields[f"{prefix}_op"] = forms.ChoiceField(choices=OP_CHOICES, required=False, widget=forms.Select(attrs={"class": "tb-input"}))
                for side in ("left", "right"):
                    self._add_expr_fields(f"{prefix}_{side}")

    def _add_expr_fields(self, prefix: str) -> None:
        self.fields[f"{prefix}_ref"] = forms.ChoiceField(choices=REF_CHOICES, required=False, widget=forms.Select(attrs={"class": "tb-input"}))
        self.fields[f"{prefix}_indicator"] = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"class": "tb-input"}))
        self.fields[f"{prefix}_price"] = forms.ChoiceField(choices=PRICE_CHOICES, required=False, widget=forms.Select(attrs={"class": "tb-input"}))
        self.fields[f"{prefix}_value"] = forms.FloatField(required=False, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))
        self.fields[f"{prefix}_param"] = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"class": "tb-input"}))

        # pct_offset: base + pct (simple nested refs)
        self.fields[f"{prefix}_po_base_ref"] = forms.ChoiceField(choices=NESTED_REF_CHOICES, required=False, widget=forms.Select(attrs={"class": "tb-input"}))
        self.fields[f"{prefix}_po_base_indicator"] = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"class": "tb-input"}))
        self.fields[f"{prefix}_po_base_price"] = forms.ChoiceField(choices=PRICE_CHOICES, required=False, widget=forms.Select(attrs={"class": "tb-input"}))
        self.fields[f"{prefix}_po_base_value"] = forms.FloatField(required=False, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))
        self.fields[f"{prefix}_po_base_param"] = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"class": "tb-input"}))
        self.fields[f"{prefix}_po_pct_ref"] = forms.ChoiceField(choices=NESTED_REF_CHOICES, required=False, widget=forms.Select(attrs={"class": "tb-input"}))
        self.fields[f"{prefix}_po_pct_value"] = forms.FloatField(required=False, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))
        self.fields[f"{prefix}_po_pct_param"] = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"class": "tb-input"}))

        # arith: op + left + right (simple nested refs)
        self.fields[f"{prefix}_ar_op"] = forms.ChoiceField(choices=ARITH_CHOICES, required=False, widget=forms.Select(attrs={"class": "tb-input"}))
        for nest in ("ar_left", "ar_right"):
            nest_prefix = f"{prefix}_{nest}"
            self.fields[f"{nest_prefix}_ref"] = forms.ChoiceField(choices=NESTED_REF_CHOICES, required=False, widget=forms.Select(attrs={"class": "tb-input"}))
            self.fields[f"{nest_prefix}_indicator"] = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"class": "tb-input"}))
            self.fields[f"{nest_prefix}_price"] = forms.ChoiceField(choices=PRICE_CHOICES, required=False, widget=forms.Select(attrs={"class": "tb-input"}))
            self.fields[f"{nest_prefix}_value"] = forms.FloatField(required=False, widget=forms.NumberInput(attrs={"class": "tb-input", "step": "any"}))
            self.fields[f"{nest_prefix}_param"] = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"class": "tb-input"}))

    def build_spec(self) -> dict[str, Any]:
        if not self.is_valid():
            raise ExprError("Form is invalid")
        data = self.cleaned_data
        spec = empty_spec()

        for i in range(MAX_PARAMS):
            name = (data.get(f"param_{i}_name") or "").strip()
            if not name:
                continue
            entry: dict[str, Any] = {
                "name": name,
                "type": data.get(f"param_{i}_type") or "float",
                "default": data.get(f"param_{i}_default") if data.get(f"param_{i}_default") is not None else 0,
            }
            if data.get(f"param_{i}_min") is not None:
                entry["min"] = data[f"param_{i}_min"]
            if data.get(f"param_{i}_max") is not None:
                entry["max"] = data[f"param_{i}_max"]
            spec["parameters"].append(entry)

        for i in range(MAX_INDICATORS):
            ind_id = (data.get(f"ind_{i}_id") or "").strip()
            fn = data.get(f"ind_{i}_fn") or ""
            if not ind_id or not fn:
                continue
            args: dict[str, Any] = {}
            period_param = (data.get(f"ind_{i}_period_param") or "").strip()
            if period_param:
                args["period"] = {"ref": "param", "name": period_param}
            elif data.get(f"ind_{i}_period") is not None:
                args["period"] = int(data[f"ind_{i}_period"])
            column = data.get(f"ind_{i}_column") or "close"
            if column:
                args["column"] = column
            source = data.get(f"ind_{i}_source") or "primary"
            spec["indicators"].append({"id": ind_id, "fn": fn, "source": source, "args": args})

        for group in ("entry_long", "entry_short", "exit_long", "exit_short"):
            rules = []
            for i in range(MAX_RULES):
                prefix = f"{group}_{i}"
                op = data.get(f"{prefix}_op") or ""
                if not op:
                    continue
                left = self._parse_expr(data, f"{prefix}_left")
                right = self._parse_expr(data, f"{prefix}_right")
                if left is None or right is None:
                    raise ExprError(f"Incomplete rule in {group} slot {i + 1}")
                rules.append({"op": op, "left": left, "right": right})
            spec[group] = {
                "logic": data.get(f"{group}_logic") or "and",
                "rules": rules,
            }

        stop_type = data.get("stop_type") or ""
        if stop_type == "pct":
            spec["stop_loss"] = {"type": "pct", "value": float(data.get("stop_pct") or 1.0)}
        elif stop_type == "atr":
            spec["stop_loss"] = {
                "type": "atr",
                "mult": float(data.get("stop_atr_mult") or 1.5),
                "period": int(data.get("stop_atr_period") or 14),
            }

        tp_type = data.get("tp_type") or ""
        if tp_type == "pct":
            spec["take_profit"] = {"type": "pct", "value": float(data.get("tp_pct") or 2.0)}
        elif tp_type == "rr":
            spec["take_profit"] = {"type": "rr", "ratio": float(data.get("tp_rr") or 2.0)}

        return validate_spec(spec)

    def _parse_expr(self, data: dict, prefix: str) -> dict | None:
        ref = data.get(f"{prefix}_ref") or ""
        if not ref:
            return None
        if ref in SIMPLE_REFS:
            return self._parse_simple(data, prefix, ref)
        if ref == "pct_offset":
            base = self._parse_simple(data, f"{prefix}_po_base", data.get(f"{prefix}_po_base_ref") or "")
            pct = self._parse_simple(data, f"{prefix}_po_pct", data.get(f"{prefix}_po_pct_ref") or "")
            if base is None or pct is None:
                return None
            return {"ref": "pct_offset", "base": base, "pct": pct}
        if ref == "arith":
            op = data.get(f"{prefix}_ar_op") or ""
            if op not in ARITH_OPS:
                return None
            left = self._parse_simple(data, f"{prefix}_ar_left", data.get(f"{prefix}_ar_left_ref") or "")
            right = self._parse_simple(data, f"{prefix}_ar_right", data.get(f"{prefix}_ar_right_ref") or "")
            if left is None or right is None:
                return None
            return {"ref": "arith", "op": op, "left": left, "right": right}
        return None

    @staticmethod
    def _parse_simple(data: dict, prefix: str, ref: str) -> dict | None:
        if ref == "indicator":
            ind_id = (data.get(f"{prefix}_indicator") or "").strip()
            if not ind_id:
                return None
            return {"ref": "indicator", "id": ind_id}
        if ref == "price":
            field = data.get(f"{prefix}_price") or "close"
            return {"ref": "price", "field": field}
        if ref == "value":
            if data.get(f"{prefix}_value") is None:
                return None
            return {"ref": "value", "value": float(data[f"{prefix}_value"])}
        if ref == "param":
            name = (data.get(f"{prefix}_param") or "").strip()
            if not name:
                return None
            return {"ref": "param", "name": name}
        return None


def _fill_simple_initial(initial: dict[str, Any], prefix: str, node: dict) -> None:
    ref = node.get("ref") or node.get("type") or ""
    if ref not in SIMPLE_REFS:
        return
    initial[f"{prefix}_ref"] = ref
    if ref == "indicator":
        initial[f"{prefix}_indicator"] = node.get("id", "")
    elif ref == "price":
        initial[f"{prefix}_price"] = node.get("field", "close")
    elif ref == "value":
        initial[f"{prefix}_value"] = node.get("value")
    elif ref == "param":
        initial[f"{prefix}_param"] = node.get("name", "")


def _fill_expr_initial(initial: dict[str, Any], prefix: str, node: dict) -> None:
    ref = node.get("ref") or node.get("type") or ""
    if ref in SIMPLE_REFS:
        _fill_simple_initial(initial, prefix, node)
        return
    if ref == "pct_offset":
        initial[f"{prefix}_ref"] = "pct_offset"
        base = node.get("base") or {}
        pct = node.get("pct") or {}
        _fill_simple_initial(initial, f"{prefix}_po_base", {**base, "ref": base.get("ref") or base.get("type")})
        # remap nested keys: _fill_simple writes prefix_ref etc; for po_base we need po_base_ref
        # _fill_simple_initial already uses prefix_ref — good for po_base
        _fill_simple_initial(initial, f"{prefix}_po_pct", {**pct, "ref": pct.get("ref") or pct.get("type")})
        return
    if ref == "arith":
        initial[f"{prefix}_ref"] = "arith"
        initial[f"{prefix}_ar_op"] = node.get("op", "")
        left = node.get("left") or {}
        right = node.get("right") or {}
        _fill_simple_initial(initial, f"{prefix}_ar_left", {**left, "ref": left.get("ref") or left.get("type")})
        _fill_simple_initial(initial, f"{prefix}_ar_right", {**right, "ref": right.get("ref") or right.get("type")})


def initial_from_spec(spec: dict[str, Any], *, name: str = "", description: str = "") -> dict[str, Any]:
    """Map a validated rule_spec into RuleBuilderForm initial data."""
    initial: dict[str, Any] = {"name": name, "description": description}
    for i, param in enumerate((spec.get("parameters") or [])[:MAX_PARAMS]):
        initial[f"param_{i}_name"] = param.get("name", "")
        initial[f"param_{i}_type"] = param.get("type", "float")
        initial[f"param_{i}_default"] = param.get("default", 0)
        if "min" in param:
            initial[f"param_{i}_min"] = param["min"]
        if "max" in param:
            initial[f"param_{i}_max"] = param["max"]

    for i, ind in enumerate((spec.get("indicators") or [])[:MAX_INDICATORS]):
        initial[f"ind_{i}_id"] = ind.get("id", "")
        initial[f"ind_{i}_fn"] = ind.get("fn", "")
        initial[f"ind_{i}_source"] = ind.get("source", "primary")
        args = ind.get("args") or {}
        period = args.get("period")
        if isinstance(period, dict) and (period.get("ref") == "param"):
            initial[f"ind_{i}_period_param"] = period.get("name", "")
        elif period is not None:
            initial[f"ind_{i}_period"] = period
        initial[f"ind_{i}_column"] = args.get("column", "close")

    for group in ("entry_long", "entry_short", "exit_long", "exit_short"):
        g = spec.get(group) or {}
        initial[f"{group}_logic"] = g.get("logic", "and")
        for i, rule in enumerate((g.get("rules") or [])[:MAX_RULES]):
            prefix = f"{group}_{i}"
            initial[f"{prefix}_op"] = rule.get("op", "")
            for side in ("left", "right"):
                _fill_expr_initial(initial, f"{prefix}_{side}", rule.get(side) or {})

    sl = spec.get("stop_loss") or {}
    if sl.get("type") == "pct":
        initial["stop_type"] = "pct"
        initial["stop_pct"] = sl.get("value")
    elif sl.get("type") == "atr":
        initial["stop_type"] = "atr"
        initial["stop_atr_mult"] = sl.get("mult")
        initial["stop_atr_period"] = sl.get("period", 14)

    tp = spec.get("take_profit") or {}
    if tp.get("type") == "pct":
        initial["tp_type"] = "pct"
        initial["tp_pct"] = tp.get("value")
    elif tp.get("type") == "rr":
        initial["tp_type"] = "rr"
        initial["tp_rr"] = tp.get("ratio")

    return initial
