"""Presentation-layer CRUD facade shared across every service.

Provides :class:`BaseController` with the same six CRUD methods as
:class:`common.api.base_use_case.BaseUseCase` and
:class:`common.api.base_repository.BaseRepository`. Default methods
delegate to the injected use case — subclasses override to translate
domain entities into Pydantic response schemas or to reject
unsupported operations.
"""

from __future__ import annotations

from typing import Any

from common.api.base_use_case import BaseUseCase


class BaseController:
    """CRUD-shaped base for presentation-layer controllers.

    Attributes:
        _use_cases: Injected use-case facade; default methods proxy to it.
    """

    def __init__(self, use_cases: BaseUseCase) -> None:
        """Inject the use-case dependency."""
        self._use_cases = use_cases

    async def get(self, id_: int) -> Any:
        """Return the entity with PK ``id_`` as a response-ready payload."""
        return await self._use_cases.get(id_)

    async def create(self, **fields: Any) -> Any:
        """Create an entity and return the response payload."""
        return await self._use_cases.create(**fields)

    async def update(self, id_: int, **fields: Any) -> Any:
        """Fully update the entity with PK ``id_``."""
        return await self._use_cases.update(id_, **fields)

    async def partial_update(self, id_: int, **fields: Any) -> Any:
        """Partially update the entity with PK ``id_``."""
        return await self._use_cases.partial_update(id_, **fields)

    async def delete(self, id_: int) -> None:
        """Delete the entity with PK ``id_``."""
        await self._use_cases.delete(id_)

    async def bulk_delete(self, ids: list[int], *, fast: bool = False) -> int:
        """Delete every entity in ``ids``. Returns the count deleted.

        ``fast=True`` runs a single queryset-level delete (skips per-row
        hooks); ``fast=False`` (default) iterates so lifecycle hooks fire.
        """
        return await self._use_cases.bulk_delete(ids, fast=fast)

    async def bulk_patch(
        self, ids: list[int], *, fast: bool = False, **fields: Any
    ) -> int:
        """Partial-update every entity in ``ids`` with ``fields``. Returns the count updated.

        ``fast=True`` runs a single queryset-level update (skips per-row
        hooks); ``fast=False`` (default) iterates so lifecycle hooks fire.
        """
        return await self._use_cases.bulk_patch(ids, fast=fast, **fields)

    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: list[str] | None = None,
        **filters: Any,
    ) -> tuple[list[Any], int]:
        """Return an offset-paginated ``(items, total)`` pair."""
        return await self._use_cases.list(
            limit=limit, offset=offset, order_by=order_by, **filters
        )

    async def list_cursor(
        self,
        *,
        cursor: str | None = None,
        limit: int = 100,
        **filters: Any,
    ) -> tuple[list[Any], str | None]:
        """Return a cursor-paginated ``(items, next_cursor)`` pair."""
        return await self._use_cases.list_cursor(cursor=cursor, limit=limit, **filters)
