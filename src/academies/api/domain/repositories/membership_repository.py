"""Abstract repository interface for the Membership aggregate.

Declares the base CRUD slots the membership use case relies on (``get`` /
``create`` / ``list`` / ``count``, returning raw ORM rows typed as
``Any``) plus the membership-specific ``set_status`` transition used by the
approve / reject flow. Pure ``abc.ABC`` with no Django import; the concrete
implementation pairs this contract with :class:`common.api.BaseRepository`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IMembershipRepository(ABC):
    """Contract that all Membership repository implementations must satisfy."""

    @abstractmethod
    async def get(self, id_: int) -> Any | None:
        """Return the membership row for the given primary key, or ``None``."""

    @abstractmethod
    async def create(self, **fields: Any) -> Any:
        """Create and return a new membership row from the given field values."""

    @abstractmethod
    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: list[str] | None = None,
        **filters: Any,
    ) -> list[Any]:
        """Return an offset-paginated page of membership rows."""

    @abstractmethod
    async def count(self, **filters: Any) -> int:
        """Return the number of membership rows matching ``filters``."""

    @abstractmethod
    async def set_status(self, id_: int, *, status: str) -> Any:
        """Transition the membership row's ``status`` and return the row.

        Args:
            id_:    Primary key of the membership row.
            status: New status (``approved`` or ``rejected``).
        """
