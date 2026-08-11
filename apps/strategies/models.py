from django.db import models


class Strategy(models.Model):
    """Configured strategy instance (library, custom Python, or rule-spec)."""

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    module_path = models.CharField(max_length=255)
    parameters = models.JSONField(default=dict, blank=True)
    rule_spec = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON rule-spec for apps.strategies.rules.runtime strategies.",
    )
    is_library = models.BooleanField(default=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    source_code = models.TextField(blank=True, help_text="Original source for custom strategies (optional audit).")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_rule_strategy(self) -> bool:
        # Require a real rule_spec. module_path alone is not enough (empty-spec rows
        # used to look like rules and broke /strategies/ edit + parameters flows).
        return bool(self.rule_spec)

    @property
    def is_custom_python(self) -> bool:
        return (not self.is_library) and (not self.is_rule_strategy) and bool(self.source_code or self.module_path.startswith("apps.strategies.user."))

    def runtime_parameters(self) -> dict:
        """Parameters dict for instantiate_strategy (embeds rule_spec when present)."""
        params = dict(self.parameters or {})
        if self.rule_spec:
            from apps.strategies.rules.runtime import RULE_SPEC_KEY

            params[RULE_SPEC_KEY] = self.rule_spec
        return params
