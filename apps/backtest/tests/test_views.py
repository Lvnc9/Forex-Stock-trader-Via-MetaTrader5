"""Backtest create/detail view tests (results experience)."""

from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.backtest.defaults import backtest_form_defaults, pick_catalog
from apps.backtest.models import BacktestRun
from apps.marketdata.catalog import InstrumentCatalog
from apps.strategies.models import Strategy


class BacktestDefaultsTests(TestCase):
    def test_pick_catalog_prefers_eurusd(self) -> None:
        catalogs = [
            InstrumentCatalog("spx", (), 0, None, None, None),
            InstrumentCatalog("eurusd", (), 0, None, None, None),
        ]
        self.assertEqual(pick_catalog(catalogs).slug, "eurusd")

    def test_backtest_form_defaults_empty_without_data_root(self) -> None:
        self.assertEqual(backtest_form_defaults(None), {})


class BacktestCreateViewTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user("bt", password="pass")
        self.strategy = Strategy.objects.create(
            name="MA test",
            slug="ma-bt-view",
            module_path="apps.strategies.library.ma_crossover",
            parameters={"fast_period": 5, "slow_period": 20},
        )
        self.client.force_login(self.user)

    def test_get_initial_prefills_strategy_from_query_param(self) -> None:
        url = reverse("backtest:create") + f"?strategy={self.strategy.pk}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        self.assertEqual(form.initial.get("strategy"), self.strategy.pk)
        self.assertEqual(resp.context["prefill_strategy"], self.strategy)

    def test_get_initial_ignores_invalid_strategy_pk(self) -> None:
        url = reverse("backtest:create") + "?strategy=99999"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("strategy", resp.context["form"].initial)
        self.assertNotIn("prefill_strategy", resp.context)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_create_redirects_to_detail(self) -> None:
        get_resp = self.client.get(reverse("backtest:create") + f"?strategy={self.strategy.pk}")
        slug = get_resp.context["form"].fields["catalog_slug"].choices[0][0]
        self.assertTrue(slug, "Need at least one catalog slug in data root for this test")

        url = reverse("backtest:create") + f"?strategy={self.strategy.pk}"
        resp = self.client.post(
            url,
            {
                "strategy": self.strategy.pk,
                "catalog_slug": slug,
                "timeframe": "M5",
                "htf_timeframe": "",
                "start": "2024-01-01",
                "end": "2024-01-02",
                "initial_balance": "10000",
                "spread_pct": "0",
                "commission": "0",
                "sizing_mode": BacktestRun.SizingMode.ALL_IN,
                "lot_size": "0.01",
                "contract_size": "100000",
            },
        )
        self.assertEqual(resp.status_code, 302)
        run = BacktestRun.objects.get()
        self.assertEqual(resp.url, reverse("backtest:detail", kwargs={"pk": run.pk}))
        self.assertEqual(run.strategy_id, self.strategy.pk)
        self.assertIn(run.status, (BacktestRun.Status.FAILED, BacktestRun.Status.COMPLETED))


class BacktestDetailViewTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user("bt2", password="pass")
        self.strategy = Strategy.objects.create(
            name="Detail strat",
            slug="detail-strat",
            module_path="apps.strategies.library.ma_crossover",
            parameters={"fast_period": 10, "slow_period": 30},
        )
        self.client.force_login(self.user)

    def _completed_run(self) -> BacktestRun:
        return BacktestRun.objects.create(
            strategy=self.strategy,
            catalog_slug="eurusd",
            timeframe="H1",
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
            initial_balance=10_000,
            status=BacktestRun.Status.COMPLETED,
            metrics={
                "win_rate_pct": 55.0,
                "net_return_pct": 3.5,
                "profit_factor": 1.2,
                "max_drawdown_pct": 2.0,
                "trade_count": 10,
                "winning_trades": 5,
                "losing_trades": 5,
                "final_balance": 10_350.0,
                "primary_label": "H1",
                "bar_count": 100,
            },
            equity_curve=[
                {"t": "2024-01-01T00:00:00+00:00", "equity": 10000},
                {"t": "2024-06-01T00:00:00+00:00", "equity": 10350},
            ],
            trades=[
                {
                    "entry_time": "2024-02-01T10:00:00+00:00",
                    "exit_time": "2024-02-01T12:00:00+00:00",
                    "side": "long",
                    "entry_price": 1.1,
                    "exit_price": 1.105,
                    "pnl": 45.0,
                    "exit_reason": "take_profit",
                }
            ],
        )

    def test_detail_shows_full_results_experience(self) -> None:
        run = self._completed_run()
        resp = self.client.get(reverse("backtest:detail", kwargs={"pk": run.pk}))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn("Strategy", content)
        self.assertIn(self.strategy.name, content)
        self.assertIn("eurusd", content)
        self.assertIn("Initial balance", content)
        self.assertIn("Final balance", content)
        self.assertIn("10000", content)
        self.assertIn("10350", content)
        self.assertIn("Account balance", content)
        self.assertIn("Win rate", content)
        self.assertIn("Profit factor", content)
        self.assertIn("Max drawdown", content)
        self.assertIn("Trades", content)
        self.assertIn("take_profit", content)
        self.assertTrue(resp.context["balance_up"])
        self.assertEqual(resp.context["final_balance"], 10_350.0)
        self.assertFalse(resp.context["is_in_progress"])

    def test_detail_progress_section_while_running(self) -> None:
        run = BacktestRun.objects.create(
            strategy=self.strategy,
            catalog_slug="eurusd",
            timeframe="M5",
            start=date(2024, 1, 1),
            end=date(2024, 1, 2),
            initial_balance=10_000,
            status=BacktestRun.Status.RUNNING,
            progress_pct=42.0,
            progress_message="Simulating",
        )
        resp = self.client.get(reverse("backtest:detail", kwargs={"pk": run.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["is_in_progress"])
        content = resp.content.decode()
        self.assertIn("Progress", content)
        self.assertIn("Simulating", content)
        self.assertIn("42", content)
        self.assertIn(reverse("backtest:status", kwargs={"pk": run.pk}), content)

    def test_detail_pending_shows_worker_hint(self) -> None:
        run = BacktestRun.objects.create(
            strategy=self.strategy,
            catalog_slug="eurusd",
            timeframe="M5",
            start=date(2024, 1, 1),
            end=date(2024, 1, 2),
            initial_balance=10_000,
            status=BacktestRun.Status.PENDING,
            progress_message="Queued",
        )
        resp = self.client.get(reverse("backtest:detail", kwargs={"pk": run.pk}))
        content = resp.content.decode()
        self.assertIn("Queued", content)
        self.assertIn("Celery", content)

    def test_detail_failed_shows_error_panel(self) -> None:
        run = BacktestRun.objects.create(
            strategy=self.strategy,
            catalog_slug="eurusd",
            timeframe="M5",
            start=date(2024, 1, 1),
            end=date(2024, 1, 2),
            initial_balance=10_000,
            status=BacktestRun.Status.FAILED,
            error_message="No bars in selected date range",
        )
        resp = self.client.get(reverse("backtest:detail", kwargs={"pk": run.pk}))
        content = resp.content.decode()
        self.assertIn("Run failed", content)
        self.assertIn("No bars in selected date range", content)
        self.assertNotIn("Account balance", content)

    def test_status_json_payload(self) -> None:
        run = self._completed_run()
        resp = self.client.get(reverse("backtest:status", kwargs={"pk": run.pk}))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], run.pk)
        self.assertEqual(data["status"], "completed")
        self.assertTrue(data["done"])
        self.assertEqual(data["initial_balance"], 10000.0)
        self.assertEqual(data["final_balance"], 10350.0)
        self.assertEqual(data["win_rate_pct"], 55.0)
