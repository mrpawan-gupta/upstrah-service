"""Mixin providing soft-delete capability for Django models.

Provides ``is_deleted`` / ``deleted_at`` fields via ``SoftDeleteMixin``.
Models that include this mixin should filter ``is_deleted=False`` in all
normal list/count queries to hide deleted records from end-users.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SoftDeleteMixin(models.Model):
    """Abstract mixin adding soft-delete semantics.

    Rows are never physically removed. :meth:`soft_delete` flips
    ``is_deleted`` and stamps ``deleted_at``; repository queries for
    user-facing data must filter ``is_deleted=False`` explicitly — there
    is no custom manager doing it implicitly, so forgetting the filter
    leaks deleted rows.

    Attributes:
        is_deleted: Tombstone flag; indexed for fast ``is_deleted=False``
            scans on large tables.
        deleted_at: Stamp of when the row was soft-deleted; ``None``
            while the row is live.
    """

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Is Deleted"),
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Deleted At"),
    )

    class Meta:
        abstract = True

    def soft_delete(self) -> None:
        """Mark this instance as deleted without removing the database row.

        Sets ``is_deleted=True`` and stamps ``deleted_at`` with the current
        UTC time, then saves only those two fields.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    async def asoft_delete(self) -> None:
        """Async variant of :meth:`soft_delete` for use inside FastAPI handlers.

        Sets ``is_deleted=True`` and stamps ``deleted_at`` with the current
        UTC time, then persists only those two fields via ``asave()``.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        await self.asave(update_fields=["is_deleted", "deleted_at"])
