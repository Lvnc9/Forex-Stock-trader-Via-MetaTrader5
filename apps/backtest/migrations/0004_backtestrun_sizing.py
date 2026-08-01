# Generated manually for backtest sizing parity fields

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backtest", "0003_backtestrun_progress"),
    ]

    operations = [
        migrations.AddField(
            model_name="backtestrun",
            name="sizing_mode",
            field=models.CharField(
                choices=[
                    ("all_in", "All-in (cash ÷ price)"),
                    ("fixed_lots", "Fixed lots (match live Deployment.lot_size)"),
                ],
                default="all_in",
                help_text="all_in compounds cash; fixed_lots matches live Deployment.lot_size.",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="backtestrun",
            name="lot_size",
            field=models.FloatField(
                default=0.01,
                help_text="Used when sizing_mode=fixed_lots (same meaning as Deployment.lot_size).",
            ),
        ),
        migrations.AddField(
            model_name="backtestrun",
            name="contract_size",
            field=models.FloatField(
                default=100000.0,
                help_text="Units per 1.0 lot (100000 for standard FX; adjust for CFDs/indices).",
            ),
        ),
    ]
