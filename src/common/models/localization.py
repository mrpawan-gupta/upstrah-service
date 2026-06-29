"""Abstract Django model mixins for bilingual name and description fields.

Provides :class:`LocalizedNameMixin` (``name_en`` / ``name_id`` + ``name``
property) and :class:`LocalizedDescriptionMixin` (``description_en`` /
``description_id`` + ``description`` property) for models that need
English/Indonesian display text.  The ``name`` / ``description`` properties
resolve to the field that matches the active Django language, falling back to
English when Indonesian is not set.
"""

from __future__ import annotations

from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _


class LocalizedNameMixin(models.Model):
    """Abstract mixin adding bilingual ``name_en`` / ``name_id`` columns.

    The ``name`` property returns the field that matches the current active
    language (``id`` → ``name_id``, anything else → ``name_en``).  If the
    language-specific field is empty the English value is returned as a
    fallback so callers never receive an empty string when ``name_en`` is set.

    Attributes:
        name_en: Display name in English.
        name_id: Display name in Indonesian (Bahasa Indonesia).
    """

    name_en = models.CharField(max_length=255, verbose_name=_("Name (EN)"))
    name_id = models.CharField(max_length=255, blank=True, verbose_name=_("Name (ID)"))

    class Meta:
        abstract = True

    @property
    def name(self) -> str:
        lang = translation.get_language()
        if lang and lang.startswith("id"):
            return self.name_id or self.name_en
        return self.name_en


class LocalizedDescriptionMixin(models.Model):
    """Abstract mixin adding bilingual ``description_en`` / ``description_id`` columns.

    The ``description`` property returns the field matching the current active
    language, falling back to English when the Indonesian value is empty.

    Attributes:
        description_en: Description in English.
        description_id: Description in Indonesian (Bahasa Indonesia).
    """

    description_en = models.TextField(blank=True, verbose_name=_("Description (EN)"))
    description_id = models.TextField(blank=True, verbose_name=_("Description (ID)"))

    class Meta:
        abstract = True

    @property
    def description(self) -> str:
        lang = translation.get_language()
        if lang and lang.startswith("id"):
            return self.description_id or self.description_en
        return self.description_en
