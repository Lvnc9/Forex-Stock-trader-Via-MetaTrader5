from django.db import models


class SymbolMap(models.Model):
    """Maps local catalog slug to broker MT5 symbol names."""

    catalog_slug = models.SlugField(max_length=80, unique=True)
    dukascopy_id = models.CharField(max_length=120, blank=True)
    mt5_symbol = models.CharField(max_length=64, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["catalog_slug"]

    def __str__(self) -> str:
        return f"{self.catalog_slug} → {self.mt5_symbol or '?'}"
