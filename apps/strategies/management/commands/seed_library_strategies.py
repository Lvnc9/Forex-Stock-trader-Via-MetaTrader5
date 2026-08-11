from django.core.management.base import BaseCommand

from apps.strategies.models import Strategy
from apps.strategies.registry import LIBRARY_STRATEGIES


class Command(BaseCommand):
    help = "Upsert built-in library strategies into the Strategy table."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for cls in LIBRARY_STRATEGIES:
            obj, was_created = Strategy.objects.update_or_create(
                slug=cls.slug,
                defaults={
                    "name": cls.name,
                    "description": cls.description,
                    "module_path": cls.module_path,
                    "parameters": cls.default_parameters,
                    "rule_spec": {},
                    "is_library": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
            self.stdout.write(f"  {'Created' if was_created else 'Updated'} {obj.name}")

        self.stdout.write(self.style.SUCCESS(f"Done ({created} created, {updated} updated)."))
