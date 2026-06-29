"""Abstract base model providing timestamps, lifecycle hooks, and serialisation.

Provides ``created_at`` / ``updated_at`` fields via ``TimeStampModel`` and a
generic ``to_dict()`` serialiser used by the webhook signal pipeline to snapshot
model state without requiring per-model mappers.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_lifecycle import LifecycleModelMixin


class TimeStampModel(LifecycleModelMixin, models.Model):
    """Abstract base with audit timestamps and ``django-lifecycle`` hooks.

    Inheriting this (directly or via :class:`CareMixin`) opts the model
    into ``@hook(AFTER_CREATE)`` / ``@hook(BEFORE_UPDATE, when=..., has_changed=True)``
    decorators. ``django_lifecycle`` is deliberately **not** in
    ``INSTALLED_APPS`` — it is used as a mixin only (see
    ``rudra-service/CLAUDE.md``).

    Example::

        from django_lifecycle import hook, AFTER_CREATE

        class MyModel(TimeStampModel):
            @hook(AFTER_CREATE)
            def on_create(self):
                ...

    Attributes:
        created_at: Row creation stamp (``auto_now_add``).
        updated_at: Last-modification stamp (``auto_now``).
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        abstract = True

    def to_dict(self) -> dict[str, Any]:
        """Serialise all concrete DB columns to a plain dict.

        Foreign-key fields are emitted using their ``attname`` (e.g.
        ``company_id`` instead of ``company``).  ``Decimal``, ``datetime``,
        ``date``, and ``UUID`` values are converted to strings so the result
        is JSON-safe.

        Returns:
            Dict mapping column names to serialisable values.
        """
        data: dict[str, Any] = {}
        for field in self._meta.get_fields():
            if not field.concrete:
                continue
            col = field.attname if hasattr(field, "attname") else field.name
            value = getattr(self, col, None)
            if isinstance(value, Decimal):
                value = str(value)
            elif isinstance(value, (datetime, date)):
                value = value.isoformat()
            elif isinstance(value, UUID):
                value = str(value)
            data[col] = value
        return data
