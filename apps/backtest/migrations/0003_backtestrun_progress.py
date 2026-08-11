# Generated manually for backtest progress fields

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backtest", "0002_htf_timeframe"),
    ]

    operations = [
        migrations.AddField(
            model_name="backtestrun",
            name="progress_pct",
            field=models.FloatField(default=0.0, help_text="0–100 while running."),
        ),
        migrations.AddField(
            model_name="backtestrun",
            name="progress_message",
            field=models.CharField(blank=True, default="", max_length=240),
        ),
    ]
