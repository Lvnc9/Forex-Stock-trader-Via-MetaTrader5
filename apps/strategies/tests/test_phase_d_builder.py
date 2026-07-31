"""Phase D: builder pct_offset/arith + HTF indicator source."""

from __future__ import annotations

import math

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from apps.strategies.context import BarContext
from apps.strategies.engine import SignalEngine
from apps.strategies.indicators.registry import IndicatorRegistry
from apps.strategies.rules.builder import RuleBuilderForm, initial_from_spec
from apps.strategies.rules.runtime import RULE_SPEC_KEY, RuleStrategy
from apps.strategies.rules.templates import get_template
from apps.strategies.validation import dry_run_rule_spec


def _bars(n: int = 120, freq: str = "5min") -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    close = pd.Series([100 + 5 * math.sin(i / 6.0) for i in range(n)], index=index, dtype=float)
    return pd.DataFrame({"open": close, "high": close + 1, "low": close - 1, "close": close}, index=index)


class PctOffsetBuilderTests(SimpleTestCase):
    def test_builds_pct_offset_and_arith(self):
        data = {
            "name": "PO",
            "param_0_name": "buffer_pct",
            "param_0_type": "float",
            "param_0_default": "0.5",
            "ind_0_id": "mid",
            "ind_0_fn": "sma",
            "ind_0_source": "primary",
            "ind_0_period": "10",
            "ind_0_column": "close",
            "entry_long_logic": "and",
            "entry_long_0_op": ">",
            "entry_long_0_left_ref": "price",
            "entry_long_0_left_price": "close",
            "entry_long_0_right_ref": "pct_offset",
            "entry_long_0_right_po_base_ref": "indicator",
            "entry_long_0_right_po_base_indicator": "mid",
            "entry_long_0_right_po_pct_ref": "param",
            "entry_long_0_right_po_pct_param": "buffer_pct",
            "entry_short_logic": "and",
            "entry_short_0_op": "<",
            "entry_short_0_left_ref": "price",
            "entry_short_0_left_price": "close",
            "entry_short_0_right_ref": "arith",
            "entry_short_0_right_ar_op": "*",
            "entry_short_0_right_ar_left_ref": "indicator",
            "entry_short_0_right_ar_left_indicator": "mid",
            "entry_short_0_right_ar_right_ref": "value",
            "entry_short_0_right_ar_right_value": "0.99",
            "exit_long_logic": "and",
            "exit_short_logic": "and",
        }
        form = RuleBuilderForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        spec = form.build_spec()
        self.assertEqual(spec["entry_long"]["rules"][0]["right"]["ref"], "pct_offset")
        self.assertEqual(spec["entry_short"]["rules"][0]["right"]["ref"], "arith")
        dry_run_rule_spec(spec)

    def test_range_breakout_round_trips_in_builder(self):
        tmpl = get_template("range_breakout_rules")
        initial = initial_from_spec(tmpl["spec"], name="RB", description="")
        form = RuleBuilderForm(data={**initial, "name": "RB"})
        # ChoiceField needs stringy POST; rebuild via initial keys as form data
        data = {k: ("" if v is None else v) for k, v in initial.items()}
        data["name"] = "RB"
        form = RuleBuilderForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        spec = form.build_spec()
        self.assertEqual(spec["entry_long"]["rules"][0]["right"]["ref"], "pct_offset")


class HtfIndicatorSourceTests(SimpleTestCase):
    def test_htf_template_needs_htf_bars(self):
        tmpl = get_template("htf_ma_filter_rules")
        strategy = RuleStrategy({RULE_SPEC_KEY: tmpl["spec"], "fast_period": 3, "slow_period": 8, "htf_sma_period": 5})
        primary = _bars(100)
        # Without HTF: no signals
        events = SignalEngine().run(strategy, primary, warmup=20)
        self.assertEqual(events, [])

        htf = primary.resample("1h").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        ).dropna()
        events_htf = SignalEngine().run(strategy, primary, htf_bars=htf, warmup=20)
        # May or may not fire depending on series; must not crash and can emit
        self.assertIsInstance(events_htf, list)

    def test_htf_indicator_uses_htf_registry(self):
        tmpl = get_template("htf_ma_filter_rules")
        strategy = RuleStrategy({RULE_SPEC_KEY: tmpl["spec"]})
        primary = _bars(80)
        htf = primary.resample("15min").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        ).dropna()
        ctx = BarContext(
            bar_index=len(primary) - 1,
            timestamp=primary.index[-1],
            bars=primary,
            parameters=strategy.parameters,
            indicators=IndicatorRegistry(primary),
            htf_bars=htf.loc[: primary.index[-1]],
        )
        # Should not raise
        strategy.on_bar(ctx)


class HtfTemplateUiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("d1", password="pass12345")
        self.client = Client()
        self.client.login(username="d1", password="pass12345")

    def test_customize_htf_template_loads(self):
        resp = self.client.get(reverse("strategies:rule_create") + "?from=htf_ma_filter_rules")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "HTF")
