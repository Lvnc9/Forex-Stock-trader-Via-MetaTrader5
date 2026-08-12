from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backtest", "0005_backtestrun_parameter_overrides"),
    ]

    operations = [
        migrations.AddField(
            model_name="backtestrun",
            name="thermal_profile",
            field=models.CharField(
                choices=[("eco", "Eco"), ("laptop", "Laptop"), ("max", "Max")],
                default="laptop",
                help_text="Thermal profile for worker budget: eco, laptop, or max.",
                max_length=16,
            ),
        ),
    ]
