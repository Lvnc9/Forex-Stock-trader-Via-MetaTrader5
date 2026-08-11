from django.core.management.base import BaseCommand

from apps.backtest.progress import fail_orphaned_runs


class Command(BaseCommand):
    help = "Mark stuck pending/running backtests as failed (orphaned)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=None,
            help="Age threshold in minutes (default: ORPHAN_RUNNING_MINUTES).",
        )
        parser.add_argument(
            "--all-stuck",
            action="store_true",
            help="Fail every pending/running run regardless of age.",
        )

    def handle(self, *args, **options):
        if options["all_stuck"]:
            minutes = 0
        else:
            minutes = options["minutes"]
        count = fail_orphaned_runs(older_than_minutes=minutes)
        self.stdout.write(self.style.SUCCESS(f"Marked {count} orphaned backtest run(s) as failed."))
