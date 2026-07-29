from django.db import models


class Strategy(models.Model):
    """Configured strategy instance (library or custom module)."""

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    module_path = models.CharField(max_length=255)
    parameters = models.JSONField(default=dict, blank=True)
    is_library = models.BooleanField(default=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    source_code = models.TextField(blank=True, help_text="Original source for custom strategies (optional audit).")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
