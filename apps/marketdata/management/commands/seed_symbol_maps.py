"""Upsert suggested SymbolMap rows for known catalog slugs."""

from django.core.management.base import BaseCommand

from apps.marketdata.instruments import DEFAULT_MT5_SYMBOLS, dukascopy_id_for_slug
from apps.marketdata.models import SymbolMap


class Command(BaseCommand):
    help = "Create/update SymbolMap rows with default MT5 names (edit per broker)."

    def handle(self, *args, **options):
        created = updated = 0
        for slug, mt5 in sorted(DEFAULT_MT5_SYMBOLS.items()):
            obj, was_created = SymbolMap.objects.update_or_create(
                catalog_slug=slug,
                defaults={
                    "dukascopy_id": dukascopy_id_for_slug(slug),
                    "mt5_symbol": mt5,
                    "notes": "Auto-seeded; verify against your broker",
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
            self.stdout.write(f"  {'Created' if was_created else 'Updated'} {obj}")

        self.stdout.write(self.style.SUCCESS(f"Done ({created} created, {updated} updated)."))
