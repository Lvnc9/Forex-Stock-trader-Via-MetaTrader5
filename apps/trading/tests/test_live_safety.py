from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from apps.brokers.models import TradingAgent
from apps.brokers.tokens import generate_agent_token, hash_agent_token
from apps.strategies.models import Strategy
from apps.trading.models import Deployment, DeploymentEvent


class LiveSafeguardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("u", password="pass")
        self.token = generate_agent_token()
        self.agent = TradingAgent.objects.create(
            name="live-agent",
            token_hash=hash_agent_token(self.token),
            account_snapshot={"trade_mode": "live", "balance": 1},
            last_heartbeat_at=timezone.now() - timedelta(minutes=10),
        )
        self.strategy = Strategy.objects.create(
            name="S",
            slug="s-live",
            module_path="apps.strategies.library.ma_crossover",
            parameters={},
        )
        self.dep = Deployment.objects.create(
            strategy=self.strategy,
            agent=self.agent,
            catalog_slug="spx",
            mt5_symbol="US500",
            status=Deployment.Status.DRAFT,
        )
        self.client = Client()
        self.client.login(username="u", password="pass")
        self.api = Client()
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def test_requires_live_confirm_even_when_offline(self):
        self.assertTrue(self.agent.is_live_account)
        self.assertFalse(self.agent.is_online)
        response = self.client.get(f"/live/{self.dep.pk}/review/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["requires_live"])

    def test_api_hides_unconfirmed_live_armed(self):
        self.dep.status = Deployment.Status.ARMED
        self.dep.live_confirmed = False
        self.dep.save()
        response = self.api.get("/api/agent/deployments", **self.auth)
        self.assertEqual(response.json()["deployments"], [])

        self.dep.live_confirmed = True
        self.dep.save()
        response = self.api.get("/api/agent/deployments", **self.auth)
        self.assertEqual(len(response.json()["deployments"]), 1)

    def test_arm_records_event(self):
        # Switch agent to demo so confirm is simpler
        self.agent.account_snapshot = {"trade_mode": "demo"}
        self.agent.save()
        response = self.client.post(
            f"/live/{self.dep.pk}/review/",
            {"acknowledge": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.dep.refresh_from_db()
        self.assertEqual(self.dep.status, Deployment.Status.ARMED)
        self.assertTrue(DeploymentEvent.objects.filter(deployment=self.dep, kind="armed").exists())
