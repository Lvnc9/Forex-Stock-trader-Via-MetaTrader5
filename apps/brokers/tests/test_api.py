import json

from django.test import Client, TestCase

from apps.brokers.models import TradingAgent
from apps.brokers.tokens import generate_agent_token, hash_agent_token
from apps.strategies.models import Strategy
from apps.trading.models import Deployment


class AgentApiTests(TestCase):
    def setUp(self):
        self.token = generate_agent_token()
        self.agent = TradingAgent.objects.create(
            name="test-agent",
            token_hash=hash_agent_token(self.token),
        )
        self.client = Client()
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def test_heartbeat_requires_auth(self):
        response = self.client.post(
            "/api/agent/heartbeat",
            data=b"{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_heartbeat_updates_agent(self):
        response = self.client.post(
            "/api/agent/heartbeat",
            data=json.dumps({"mt5_connected": True, "account": {"trade_mode": "demo", "balance": 1000}}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 200)
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.mt5_connected)
        self.assertTrue(self.agent.is_online)

    def test_deployments_lists_armed(self):
        strategy = Strategy.objects.create(
            name="S",
            slug="s-test",
            module_path="apps.strategies.library.ma_crossover",
            parameters={},
        )
        Deployment.objects.create(
            strategy=strategy,
            agent=self.agent,
            catalog_slug="spx",
            mt5_symbol="US500",
            status=Deployment.Status.ARMED,
        )
        response = self.client.get("/api/agent/deployments", **self.auth)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["deployments"]), 1)
        self.assertEqual(data["deployments"][0]["module_path"], strategy.module_path)
