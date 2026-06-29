"""Async Django-ORM CRUD base shared by every repository in the platform.

Concrete repositories set ``model = MyModel`` (and optionally
``default_ordering``) and inherit six working CRUD methods plus
``count``, ``list``, and cursor-paginated ``list_cursor``. Override any
method for custom ``select_related`` / ``prefetch_related`` / validation.

The base is Django-specific by design — every Tolaram microservice
uses Django, so a neutral ``Django`` prefix in the class name added
no information.
"""

from __future__ import annotations

import base64
from typing import Any

from django.db import models


class BaseRepository:
    """Async Django-ORM CRUD base for every repository in the platform.

    Attributes:
        model:            Django model subclass this repo operates on.
        default_ordering: Default ``order_by`` applied to ``list``
                          queries when the caller does not pass an
                          explicit ``order_by``. Example: ``["-created_at"]``.
    """

    model: type[models.Model]
    default_ordering: list[str] = []

    async def get(self, id_: int) -> models.Model | None:
        """Fetch by Django PK; composite-key lookups belong on the subclass."""
        try:
            return await self.model.objects.aget(pk=id_)
        except self.model.DoesNotExist:
            return None

    async def create(self, **fields: Any) -> models.Model:
        """Create and return a new instance with the given field values."""
        return await self.model.objects.acreate(**fields)

    async def update(self, id_: int, **fields: Any) -> models.Model:
        """Update the rows named in ``fields`` on the row with PK ``id_``."""
        instance = await self.model.objects.aget(pk=id_)
        for field, value in fields.items():
            setattr(instance, field, value)
        await instance.asave(update_fields=list(fields.keys()))
        return instance

    async def partial_update(self, id_: int, **fields: Any) -> models.Model:
        """Alias of :meth:`update` — kept for shape-symmetry with the upper layers."""
        return await self.update(id_, **fields)

    async def delete(self, id_: int) -> None:
        """Hard-delete the row with PK ``id_``."""
        await self.model.objects.filter(pk=id_).adelete()

    async def bulk_delete(self, ids: list[int], *, fast: bool = False) -> int:
        """Delete every row whose PK appears in ``ids``. Returns the count.

        Args:
            ids:  List of primary keys to delete.
            fast: If ``False`` (default), iterate :meth:`delete` so
                  subclasses that override ``delete`` (for soft-delete,
                  lifecycle-hook firing, etc.) automatically inherit
                  correct bulk behaviour — at the cost of ``N`` queries.
                  If ``True``, run a single queryset-level
                  ``filter(pk__in=ids).adelete()``. That skips every
                  per-row model hook / signal; use it only when the
                  caller knows no downstream state depends on those
                  hooks firing.
        """
        if fast:
            deleted, _ = await self.model.objects.filter(pk__in=ids).adelete()
            return deleted
        deleted = 0
        for id_ in ids:
            await self.delete(id_)
            deleted += 1
        return deleted

    async def bulk_patch(
        self, ids: list[int], *, fast: bool = False, **fields: Any
    ) -> int:
        """Partial-update every row in ``ids`` with ``fields``. Returns the count.

        Args:
            ids:    List of primary keys to patch.
            fast:   If ``False`` (default), iterate
                    :meth:`partial_update` so subclasses that override
                    ``partial_update`` / ``update`` (for soft-delete
                    filtering, lifecycle-hook firing, etc.) automatically
                    inherit correct bulk behaviour — at the cost of ``N``
                    queries. Missing rows are silently skipped. If
                    ``True``, run a single queryset-level
                    ``filter(pk__in=ids).aupdate(**fields)``. That skips
                    every per-row hook / signal; use only when downstream
                    state does not depend on those hooks firing.
            fields: Native Django field assignments forwarded to the
                    underlying ``partial_update`` / ``aupdate``.
        """
        if fast:
            return await self.model.objects.filter(pk__in=ids).aupdate(**fields)
        updated = 0
        for id_ in ids:
            try:
                await self.partial_update(id_, **fields)
            except self.model.DoesNotExist:
                continue
            updated += 1
        return updated

    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: list[str] | None = None,
        **filters: Any,
    ) -> list[models.Model]:
        """Return an offset-paginated page of rows.

        Args:
            limit:    Max rows to return (default 100).
            offset:   Rows to skip.
            order_by: Optional explicit ordering. Falls back to
                      ``self.default_ordering`` when ``None``.
            **filters: Native Django field lookups passed to ``.filter()``.
        """
        qs = self.model.objects.filter(**filters)
        ordering = order_by or self.default_ordering
        if ordering:
            qs = qs.order_by(*ordering)
        qs = qs[offset : offset + limit]
        return [obj async for obj in qs]

    async def list_cursor(
        self,
        *,
        cursor: str | None = None,
        limit: int = 100,
        **filters: Any,
    ) -> tuple[list[models.Model], str | None]:
        """Return a cursor-paginated page plus the next cursor.

        The cursor is a base64-url-encoded stringified PK — opaque to
        clients. ``next_cursor`` is ``None`` when the client has
        reached the end. Subclasses whose natural ordering is non-PK
        (e.g. ``["-created_at"]``) should override this method to
        encode a ``(sort_value, pk)`` pair so pages stay stable under
        concurrent writes; the default is safe but assumes ascending-PK
        order.

        Args:
            cursor:   Opaque cursor from a previous call, or ``None`` to
                      start from the beginning.
            limit:    Max rows per page.
            **filters: Native Django field lookups.
        """
        qs = self.model.objects.filter(**filters)
        if cursor is not None:
            last_pk = int(base64.urlsafe_b64decode(cursor.encode()).decode())
            qs = qs.filter(pk__gt=last_pk)
        qs = qs.order_by("pk")[: limit + 1]
        items = [obj async for obj in qs]

        next_cursor: str | None = None
        if len(items) > limit:
            items = items[:limit]
            next_cursor = base64.urlsafe_b64encode(str(items[-1].pk).encode()).decode()
        return items, next_cursor

    async def count(self, **filters: Any) -> int:
        """Return the number of rows matching ``filters``."""
        return await self.model.objects.filter(**filters).acount()
