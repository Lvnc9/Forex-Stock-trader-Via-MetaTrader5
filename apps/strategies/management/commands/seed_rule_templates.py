from copy import deepcopy

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.strategies.models import Strategy
from apps.strategies.rules.runtime import RuleStrategy
from apps.strategies.rules.templates import RULE_TEMPLATES, get_template


class Command(BaseCommand):
    help = "Upsert rule-spec templates into the Strategy table (customize later in the builder)."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for slug in RULE_TEMPLATES:
            meta = get_template(slug)
            if not meta:
                continue
            defaults = {p["name"]: p.get("default", 0) for p in meta["spec"].get("parameters") or []}
            obj, was_created = Strategy.objects.update_or_create(
                slug=slugify(slug)[:80],
                defaults={
                    "name": meta["name"],
                    "description": meta["description"],
                    "module_path": RuleStrategy.module_path,
                    "parameters": defaults,
                    "rule_spec": deepcopy(meta["spec"]),
                    "is_library": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
            self.stdout.write(f"  {'Created' if was_created else 'Updated'} {obj.name} ({obj.slug})")

        self.stdout.write(self.style.SUCCESS(f"Done ({created} created, {updated} updated)."))
