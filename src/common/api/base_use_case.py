"""Application-layer CRUD facade shared across every service.

Provides :class:`BaseUseCase` with the same six CRUD methods as
:class:`common.api.base_controller.BaseController` and
:class:`common.api.base_repository.BaseRepository`. Default methods
delegate to the injected repository — subclasses override only to
add domain rules (validation, cross-entity invariants,
event-publication).
"""

from __future__ import annotations

from typing import Any

from common.api.base_repository import BaseRepository


class BaseUseCase:
    """CRUD-shaped base for application-layer use cases.

    Attributes:
        _repository: Injected repository; default methods proxy to it.
    """

    def __init__(self, repository: BaseRepository) -> None:
        """Inject the repository dependency."""
        self._repository = repository

    async def get(self, id_: int) -> Any:
        """Return the entity with PK ``id_`` or ``None``."""
        return await self._repository.get(id_)

    async def create(self, **fields: Any) -> Any:
        """Create an entity with the given field values."""
        return await self._repository.create(**fields)

    async def update(self, id_: int, **fields: Any) -> Any:
        """Fully update the entity with PK ``id_``."""
        return await self._repository.update(id_, **fields)

    async def partial_update(self, id_: int, **fields: Any) -> Any:
        """Partially update the entity with PK ``id_``."""
        return await self._repository.partial_update(id_, **fields)

    async def delete(self, id_: int) -> None:
        """Delete the entity with PK ``id_``."""
        await self._repository.delete(id_)

    async def bulk_delete(self, ids: list[int], *, fast: bool = False) -> int:
        """Delete every entity in ``ids``. Returns the count deleted.

        ``fast=True`` runs a single queryset-level delete (skips per-row
        hooks); ``fast=False`` (default) iterates so lifecycle hooks fire.
        """
        return await self._repository.bulk_delete(ids, fast=fast)

    async def bulk_patch(
        self, ids: list[int], *, fast: bool = False, **fields: Any
    ) -> int:
        """Partial-update every entity in ``ids`` with ``fields``. Returns the count updated.

        ``fast=True`` runs a single queryset-level update (skips per-row
        hooks); ``fast=False`` (default) iterates so lifecycle hooks fire.
        """
        return await self._repository.bulk_patch(ids, fast=fast, **fields)

    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: list[str] | None = None,
        **filters: Any,
    ) -> tuple[list[Any], int]:
        """Return ``(items, total_count)`` for the given offset page.

        Pairs the repository's ``list`` and ``count`` calls so the
        presentation layer can build the pagination meta in one hop.
        """
        items = await self._repository.list(
            limit=limit, offset=offset, order_by=order_by, **filters
        )
        total = await self._repository.count(**filters)
        return items, total

    async def list_cursor(
        self,
        *,
        cursor: str | None = None,
        limit: int = 100,
        **filters: Any,
    ) -> tuple[list[Any], str | None]:
        """Cursor-paginated delegate. Returns ``(items, next_cursor)``."""
        return await self._repository.list_cursor(cursor=cursor, limit=limit, **filters)
