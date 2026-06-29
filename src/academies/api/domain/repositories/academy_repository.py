"""Abstract repository interface for the Academy aggregate.

Declares the base CRUD slots the academy use case relies on (``get`` /
``create`` / ``update`` / ``partial_update`` / ``delete`` / ``list`` /
``count``, returning raw ORM rows typed as ``Any``). Pure ``abc.ABC`` with
no Django import; the concrete implementation pairs this contract with
:class:`common.api.BaseRepository`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IAcademyRepository(ABC):
    """Contract that all Academy repository implementations must satisfy."""

    @abstractmethod
    async def get(self, id_: int) -> Any | None:
        """Return the academy row for the given primary key, or ``None``."""

    @abstractmethod
    async def create(self, **fields: Any) -> Any:
        """Create and return a new academy row from the given field values."""

    @abstractmethod
    async def update(self, id_: int, **fields: Any) -> Any:
        """Fully update the academy row with PK ``id_`` and return it."""

    @abstractmethod
    async def partial_update(self, id_: int, **fields: Any) -> Any:
        """Partially update the academy row with PK ``id_`` and return it."""

    @abstractmethod
    async def delete(self, id_: int) -> None:
        """Hard-delete the academy row with the given primary key."""

    @abstractmethod
    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: list[str] | None = None,
        **filters: Any,
    ) -> list[Any]:
        """Return an offset-paginated page of academy rows."""

    @abstractmethod
    async def count(self, **filters: Any) -> int:
        """Return the number of academy rows matching ``filters``."""
