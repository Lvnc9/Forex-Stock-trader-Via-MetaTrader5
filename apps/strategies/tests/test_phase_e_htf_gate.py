"""Phase E: HTF gate on forms, seed_rule_templates, LiveWorker HTF+rules smoke."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from apps.backtest.forms import BacktestRunForm
from apps.strategies.models import Strategy
from apps.strategies.rules.htf_gate import rule_spec_requires_htf, strategy_requires_htf
from apps.strategies.rules.runtime import RULE_SPEC_KEY, RuleStrategy
from apps.strategies.rules.templates import get_template
from apps.trading.forms import DeploymentDraftForm


def _bars(n: int = 120, freq: str = "5min") -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    close = pd.Series([100 + 5 * math.sin(i / 6.0) for i in range(n)], index=index, dtype=float)
    return pd.DataFrame({"open": close, "high": close + 1, "low": close - 1, "close": close}, index=index)


class HtfGateHelperTests(SimpleTestCase):
    def test_detects_htf_source(self):
        tmpl = get_template("htf_ma_filter_rules")
        self.assertTrue(rule_spec_requires_htf(tmpl["spec"]))
        self.assertFalse(rule_spec_requires_htf(get_template("ma_cross_rules")["spec"]))


class HtfGateFormTests(TestCase):
    def setUp(self):
        tmpl = get_template("htf_ma_filter_rules")
        self.htf_strategy = Strategy.objects.create(
            name="HTF rules",
            slug="htf-gate-test",
            module_path="apps.strategies.rules.runtime",
            parameters={p["name"]: p["default"] for p in tmpl["spec"]["parameters"]},
            rule_spec=tmpl["spec"],
            is_library=False,
        )
        self.assertTrue(strategy_requires_htf(self.htf_strategy))

    def test_backtest_requires_htf(self):
        form = BacktestRunForm(
            data={
                "strategy": self.htf_strategy.pk,
                "catalog_slug": "",
                "timeframe": "M5",
                "htf_timeframe": "",
                "start": "2024-01-01",
                "end": "2024-01-10",
                "initial_balance": "10000",
                "spread_pct": "0",
                "commission": "0",
            },
            data_root=None,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("htf_timeframe", form.errors)

    def test_backtest_accepts_htf(self):
        form = BacktestRunForm(
            data={
                "strategy": self.htf_strategy.pk,
                "catalog_slug": "",
                "timeframe": "M5",
                "htf_timeframe": "H1",
                "start": "2024-01-01",
                "end": "2024-01-10",
                "initial_balance": "10000",
                "spread_pct": "0",
                "commission": "0",
            },
            data_root=None,
        )
        # catalog_slug may still fail; HTF field must be clean
        form.is_valid()
        self.assertNotIn("htf_timeframe", form.errors)

    def test_deploy_requires_htf(self):
        form = DeploymentDraftForm(
            data={
                "strategy": self.htf_strategy.pk,
                "agent": "",
                "catalog_slug": "",
                "mt5_symbol": "EURUSD",
                "timeframe": "M5",
                "htf_timeframe": "",
                "lot_size": "0.01",
                "notes": "",
            },
            data_root=None,
        )
        form.is_valid()
        self.assertIn("htf_timeframe", form.errors)


class SeedRuleTemplatesTests(TestCase):
    def test_seed_creates_rows(self):
        call_command("seed_rule_templates")
        self.assertTrue(Strategy.objects.filter(slug="htf_ma_filter_rules").exists())
        obj = Strategy.objects.get(slug="htf_ma_filter_rules")
        self.assertTrue(obj.is_rule_strategy)
        self.assertTrue(strategy_requires_htf(obj))


@dataclass
class _FakeAdapter:
    connected: bool = True
    primary: pd.DataFrame = field(default_factory=pd.DataFrame)
    htf: pd.DataFrame = field(default_factory=pd.DataFrame)
    calls: list[tuple[str, str]] = field(default_factory=list)

    def copy_rates_df(self, symbol: str, timeframe: str, count: int = 400):
        self.calls.append((symbol, timeframe))
        if timeframe.upper() in {"H1", "H4", "D1"}:
            return self.htf.copy()
        return self.primary.copy()

    def open_side_for(self, symbol: str):
        return None

    def execute_signal(self, symbol, action, lot, **kwargs):
        return {"symbol": symbol, "action": action, "lot": lot, **kwargs}


class LiveWorkerRuleHtfSmokeTests(SimpleTestCase):
    def test_rule_strategy_with_htf_payload(self):
        from agent.live_worker import LiveWorker

        primary = _bars(100, freq="5min")
        htf = primary.resample("1h").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        ).dropna()
        adapter = _FakeAdapter(primary=primary, htf=htf)
        tmpl = get_template("htf_ma_filter_rules")
        params = {p["name"]: p["default"] for p in tmpl["spec"]["parameters"]}
        params[RULE_SPEC_KEY] = tmpl["spec"]
        params["fast_period"] = 3
        params["slow_period"] = 8
        params["htf_sma_period"] = 5

        worker = LiveWorker(adapter=adapter)
        reports = worker.process_deployments(
            [
                {
                    "id": 42,
                    "mt5_symbol": "EURUSD",
                    "timeframe": "M5",
                    "htf_timeframe": "H1",
                    "lot_size": 0.01,
                    "module_path": RuleStrategy.module_path,
                    "parameters": params,
                }
            ]
        )
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["status"], "processed")
        self.assertIn(("EURUSD", "M5"), adapter.calls)
        self.assertIn(("EURUSD", "H1"), adapter.calls)
