from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from io import StringIO

from apps.strategies.position_intent import resolve_signal_intent
from apps.strategies.signals import Signal, SignalAction


class PositionIntentTests(SimpleTestCase):
    def test_exit_closes(self):
        intent = resolve_signal_intent(Signal(SignalAction.EXIT), "long")
        self.assertTrue(intent.close_first)
        self.assertIsNone(intent.open_side)

    def test_same_side_noop(self):
        intent = resolve_signal_intent(
            Signal(SignalAction.ENTER_LONG, stop_loss=1.0, take_profit=2.0),
            "long",
        )
        self.assertFalse(intent.close_first)
        self.assertIsNone(intent.open_side)

    def test_flip_closes_then_opens(self):
        intent = resolve_signal_intent(
            Signal(SignalAction.ENTER_SHORT, stop_loss=1.1, take_profit=0.9),
            "long",
        )
        self.assertTrue(intent.close_first)
        self.assertEqual(intent.open_side, "short")
        self.assertEqual(intent.stop_loss, 1.1)


class DownloadBarsCommandTests(TestCase):
    def test_dry_run_fx_majors(self):
        out = StringIO()
        call_command(
            "download_bars",
            "--fx-majors",
            "--from",
            "2024-01-01",
            "--to",
            "2024-01-02",
            "--dry-run",
            stdout=out,
        )
        text = out.getvalue()
        self.assertIn("eurusd", text)
        self.assertIn("dukascopy-node", text)

    def test_stocks_dry_run(self):
        out = StringIO()
        call_command(
            "download_stocks",
            "--ticker",
            "AAPL",
            "--dry-run",
            stdout=out,
        )
        self.assertIn("AAPL", out.getvalue())
