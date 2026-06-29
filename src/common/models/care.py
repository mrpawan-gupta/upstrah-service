"""Abstract Django model mixin for CARE system reference fields.

Provides ``care_fldid``, ``care_value``, and ``care_desc`` columns that link
a catalogue item to an external CARE system record.  Include this mixin in
any model that needs to store CARE identifiers without further configuration.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class CareMixin(models.Model):
    """Abstract mixin linking a catalogue row to a CARE reference entry.

    The three columns together represent one CARE lookup result; they
    are stored on the row (rather than joined through a FK) because
    CARE is an external system of record and cross-environment FK
    integrity cannot be guaranteed.

    Attributes:
        care_fldid: CARE field identifier.
        care_value: Value paired with ``care_fldid``.
        care_desc: Human-readable description for the entry.
    """

    care_fldid = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Care Field ID")
    )
    care_value = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("Care Value")
    )
    care_desc = models.TextField(
        null=True, blank=True, verbose_name=_("Care Description")
    )

    class Meta:
        abstract = True
