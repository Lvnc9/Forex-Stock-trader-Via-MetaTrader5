from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.strategies.validation import check_custom_strategy_source, install_custom_strategy_source


SAMPLE_STRATEGY = '''
from apps.strategies.base import BaseStrategy
from apps.strategies.context import BarContext
from apps.strategies.signals import Signal, SignalAction

class AlwaysLongStrategy(BaseStrategy):
    slug = "always_long"
    name = "Always long"
    module_path = "apps.strategies.user.placeholder"
    default_parameters = {}
    parameter_schema = []

    def on_bar(self, ctx: BarContext):
        if ctx.bar_index == 20:
            return Signal(SignalAction.ENTER_LONG)
        return None
'''


class CustomValidationTests(SimpleTestCase):
    def test_check_rejects_empty(self):
        with self.assertRaises(ValidationError):
            check_custom_strategy_source("")

    def test_install_writes_and_imports(self):
        source = SAMPLE_STRATEGY.replace(
            'module_path = "apps.strategies.user.placeholder"',
            "",
        )
        module_path = install_custom_strategy_source(source)
        self.assertTrue(module_path.startswith("apps.strategies.user.custom_"))
