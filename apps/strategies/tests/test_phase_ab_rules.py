"""Phase A/B: rule engine + builder UI."""

from __future__ import annotations

import math

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from apps.backtest.models import BacktestRun
from apps.strategies.engine import SignalEngine
from apps.strategies.models import Strategy
from apps.strategies.rules.builder import RuleBuilderForm
from apps.strategies.rules.expr import ExprError
from apps.strategies.rules.runtime import RULE_SPEC_KEY, RuleStrategy
from apps.strategies.rules.schema import validate_spec
from apps.strategies.rules.templates import get_template
from apps.strategies.validation import dry_run_rule_spec, update_custom_strategy_source


def _bars(n: int = 120) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    close = pd.Series([100 + 5 * math.sin(i / 6.0) for i in range(n)], index=index, dtype=float)
    return pd.DataFrame({"open": close, "high": close + 1, "low": close - 1, "close": close}, index=index)


class RuleSpecEngineTests(SimpleTestCase):
    def test_ma_cross_template_emits_signals(self):
        tmpl = get_template("ma_cross_rules")
        self.assertIsNotNone(tmpl)
        strategy = RuleStrategy({RULE_SPEC_KEY: tmpl["spec"], "fast_period": 3, "slow_period": 8})
        events = SignalEngine().run(strategy, _bars(150), warmup=20)
        self.assertTrue(any(e.signal.action.value.startswith("enter") for e in events))

    def test_unknown_indicator_ref_raises(self):
        bad = {
            "version": 1,
            "parameters": [],
            "indicators": [],
            "entry_long": {
                "logic": "and",
                "rules": [
                    {
                        "op": ">",
                        "left": {"ref": "indicator", "id": "missing"},
                        "right": {"ref": "value", "value": 1},
                    }
                ],
            },
            "entry_short": {"logic": "and", "rules": []},
            "exit_long": {"logic": "and", "rules": []},
            "exit_short": {"logic": "and", "rules": []},
        }
        with self.assertRaises(ExprError):
            validate_spec(bad)

    def test_pct_offset_template_validates(self):
        tmpl = get_template("range_breakout_rules")
        dry_run_rule_spec(tmpl["spec"])


class RuleBuilderFormTests(SimpleTestCase):
    def test_blank_submission_fails_name(self):
        form = RuleBuilderForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_builds_spec_from_slots(self):
        data = {
            "name": "Demo",
            "description": "",
            "param_0_name": "fast",
            "param_0_type": "int",
            "param_0_default": "5",
            "param_1_name": "slow",
            "param_1_type": "int",
            "param_1_default": "20",
            "ind_0_id": "f",
            "ind_0_fn": "sma",
            "ind_0_period_param": "fast",
            "ind_0_column": "close",
            "ind_1_id": "s",
            "ind_1_fn": "sma",
            "ind_1_period_param": "slow",
            "ind_1_column": "close",
            "entry_long_logic": "and",
            "entry_long_0_op": "cross_above",
            "entry_long_0_left_ref": "indicator",
            "entry_long_0_left_indicator": "f",
            "entry_long_0_right_ref": "indicator",
            "entry_long_0_right_indicator": "s",
            "entry_short_logic": "and",
            "exit_long_logic": "and",
            "exit_short_logic": "and",
            "stop_type": "pct",
            "stop_pct": "1",
            "tp_type": "rr",
            "tp_rr": "2",
        }
        form = RuleBuilderForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        spec = form.build_spec()
        self.assertEqual(len(spec["indicators"]), 2)
        dry_run_rule_spec(spec)


class RuleStrategyUiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("u1", password="pass12345")
        self.client = Client()
        self.client.login(username="u1", password="pass12345")

    def test_create_edit_delete_rule_strategy(self):
        tmpl = get_template("ma_cross_rules")
        create = self.client.get(reverse("strategies:rule_create") + "?from=ma_cross_rules")
        self.assertEqual(create.status_code, 200)

        data = {
            "name": "My MA rules",
            "description": "test",
            "param_0_name": "fast_period",
            "param_0_type": "int",
            "param_0_default": "10",
            "param_1_name": "slow_period",
            "param_1_type": "int",
            "param_1_default": "30",
            "ind_0_id": "fast",
            "ind_0_fn": "sma",
            "ind_0_period_param": "fast_period",
            "ind_0_column": "close",
            "ind_1_id": "slow",
            "ind_1_fn": "sma",
            "ind_1_period_param": "slow_period",
            "ind_1_column": "close",
            "entry_long_logic": "and",
            "entry_long_0_op": "cross_above",
            "entry_long_0_left_ref": "indicator",
            "entry_long_0_left_indicator": "fast",
            "entry_long_0_right_ref": "indicator",
            "entry_long_0_right_indicator": "slow",
            "entry_short_logic": "and",
            "exit_long_logic": "and",
            "exit_short_logic": "and",
            "stop_type": "",
            "tp_type": "",
        }
        resp = self.client.post(reverse("strategies:rule_create"), data)
        self.assertEqual(resp.status_code, 302)
        strategy = Strategy.objects.get(name="My MA rules")
        self.assertTrue(strategy.is_rule_strategy)

        edit = self.client.get(reverse("strategies:rule_edit", args=[strategy.pk]))
        self.assertEqual(edit.status_code, 200)

        del_resp = self.client.post(reverse("strategies:delete", args=[strategy.pk]))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(Strategy.objects.filter(pk=strategy.pk).exists())

    def test_delete_blocked_by_backtest(self):
        strategy = Strategy.objects.create(
            name="Protected",
            slug="protected-rule",
            module_path="apps.strategies.rules.runtime",
            rule_spec=get_template("ma_cross_rules")["spec"],
            parameters={"fast_period": 10, "slow_period": 30},
            is_library=False,
        )
        BacktestRun.objects.create(
            strategy=strategy,
            catalog_slug="x",
            timeframe="M5",
            start="2024-01-01",
            end="2024-01-02",
        )
        resp = self.client.post(reverse("strategies:delete", args=[strategy.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Strategy.objects.filter(pk=strategy.pk).exists())

    def test_unknown_indicator_inline_error(self):
        data = {
            "name": "Bad",
            "ind_0_id": "only",
            "ind_0_fn": "sma",
            "ind_0_period": "10",
            "ind_0_column": "close",
            "entry_long_logic": "and",
            "entry_long_0_op": ">",
            "entry_long_0_left_ref": "indicator",
            "entry_long_0_left_indicator": "missing",
            "entry_long_0_right_ref": "value",
            "entry_long_0_right_value": "1",
            "entry_short_logic": "and",
            "exit_long_logic": "and",
            "exit_short_logic": "and",
        }
        resp = self.client.post(reverse("strategies:rule_create"), data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unknown indicator")


class CustomPythonLifecycleTests(TestCase):
    def test_update_in_place(self):
        from apps.strategies.validation import install_custom_strategy_source

        source_v1 = '''
from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext

class S(BaseStrategy):
    module_path = "PLACEHOLDER"
    def on_bar(self, ctx: BarContext):
        return None
'''
        # install writes its own module_path on class via file — class module_path unused for load
        source_v1 = """
from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext

class S(BaseStrategy):
    slug = "s"
    name = "S"
    module_path = "apps.strategies.user.will_be_ignored"
    def on_bar(self, ctx: BarContext):
        return None
"""
        path = install_custom_strategy_source(source_v1)
        source_v2 = source_v1.replace('name = "S"', 'name = "S2"')
        updated = update_custom_strategy_source(path, source_v2)
        self.assertEqual(updated, path)
        from pathlib import Path
        from django.conf import settings

        text = (Path(settings.BASE_DIR) / "apps/strategies/user" / f"{path.split('.')[-1]}.py").read_text()
        self.assertIn('name = "S2"', text)
