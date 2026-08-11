from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.marketdata.models import SymbolMap
from apps.strategies.models import Strategy
from apps.trading.forms import DeploymentDraftForm


class SymbolMapUiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("mapper", password="pass")
        self.client = Client()
        self.client.login(username="mapper", password="pass")

    def test_create_symbol_map(self):
        response = self.client.post(
            "/data/symbols/new/",
            {
                "catalog_slug": "spx",
                "dukascopy_id": "usa500idxusd",
                "mt5_symbol": "US500",
                "notes": "test",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SymbolMap.objects.filter(catalog_slug="spx", mt5_symbol="US500").exists())

    def test_deploy_form_requires_map_or_manual(self):
        Strategy.objects.create(
            name="S",
            slug="s-map",
            module_path="apps.strategies.library.ma_crossover",
            parameters={},
        )
        form = DeploymentDraftForm(
            data={
                "strategy": "1",
                "agent": "",
                "catalog_slug": "missing",
                "mt5_symbol": "",
                "timeframe": "M5",
                "lot_size": "0.01",
                "notes": "",
            },
            data_root=None,
        )
        # Without agents/strategies setup fully — clean() path for slug without map
        # Build a minimal valid-enough form by skipping FK: call clean logic via SymbolMap path
        SymbolMap.objects.create(catalog_slug="eurusd", mt5_symbol="EURUSD")
        from apps.brokers.models import TradingAgent
        from apps.brokers.tokens import generate_agent_token, hash_agent_token

        agent = TradingAgent.objects.create(
            name="a",
            token_hash=hash_agent_token(generate_agent_token()),
        )
        strategy = Strategy.objects.get(slug="s-map")
        form = DeploymentDraftForm(
            data={
                "strategy": str(strategy.pk),
                "agent": str(agent.pk),
                "catalog_slug": "eurusd",
                "mt5_symbol": "",
                "timeframe": "M5",
                "lot_size": "0.01",
                "notes": "",
            },
            data_root=None,
        )
        # catalog_slug choices empty when no data_root — inject
        form.fields["catalog_slug"].choices = [("eurusd", "eurusd"), ("nomap", "nomap")]
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["mt5_symbol"], "EURUSD")

        form2 = DeploymentDraftForm(
            data={
                "strategy": str(strategy.pk),
                "agent": str(agent.pk),
                "catalog_slug": "nomap",
                "mt5_symbol": "",
                "timeframe": "M5",
                "lot_size": "0.01",
                "notes": "",
            },
            data_root=None,
        )
        form2.fields["catalog_slug"].choices = [("eurusd", "eurusd"), ("nomap", "nomap")]
        self.assertFalse(form2.is_valid())
