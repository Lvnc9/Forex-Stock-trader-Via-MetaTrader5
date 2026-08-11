# Generated manually for parameter_overrides (param sweeps)

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backtest", "0004_backtestrun_sizing"),
    ]

    operations = [
        migrations.AddField(
            model_name="backtestrun",
            name="parameter_overrides",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Merged over strategy.runtime_parameters() for this run (param sweeps).",
            ),
        ),
    ]
