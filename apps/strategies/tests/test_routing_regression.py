"""Regression: strategy list / rule-edit routing guards."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.strategies.models import Strategy
from apps.strategies.rules.templates import get_template


class StrategyRoutingRegressionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("u", password="p")
        self.client.login(username="u", password="p")

    def test_list_ok(self):
        r = self.client.get(reverse("strategies:list"))
        self.assertEqual(r.status_code, 200)

    def test_empty_rule_spec_is_not_rule_strategy(self):
        s = Strategy.objects.create(
            name="Lib-like",
            slug="lib-like",
            module_path="apps.strategies.rules.runtime",
            parameters={},
            rule_spec={},
            is_library=True,
        )
        self.assertFalse(s.is_rule_strategy)

    def test_rule_edit_rejects_python_library_strategy(self):
        s = Strategy.objects.create(
            name="MA",
            slug="ma-py",
            module_path="apps.strategies.library.ma_crossover",
            parameters={"fast_period": 10, "slow_period": 30},
            rule_spec={},
            is_library=True,
        )
        r = self.client.get(reverse("strategies:rule_edit", kwargs={"pk": s.pk}))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("strategies:parameters", kwargs={"pk": s.pk}))

    def test_rule_edit_allows_real_rule_strategy(self):
        tmpl = get_template("ma_cross_rules")
        s = Strategy.objects.create(
            name=tmpl["name"],
            slug="ma-rules-row",
            module_path="apps.strategies.rules.runtime",
            parameters={"fast_period": 10, "slow_period": 30},
            rule_spec=tmpl["spec"],
            is_library=True,
        )
        r = self.client.get(reverse("strategies:rule_edit", kwargs={"pk": s.pk}))
        self.assertEqual(r.status_code, 200)
