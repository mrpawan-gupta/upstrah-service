"""Abstract repository interface for OTP persistence.

Declares the base CRUD slots the OTP use case relies on (``get`` /
``list`` / ``count`` / ``delete``, returning raw ORM rows typed as
``Any``) alongside the OTP-specific query methods (``get_or_create`` /
``get_by_phone`` / ``save`` / ``delete_row``). It stays a pure
``abc.ABC`` with no Django import; the concrete implementation pairs this
contract with :class:`common.api.BaseRepository`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IOTPRepository(ABC):
    """Contract that all OTP repository implementations must satisfy."""

    @abstractmethod
    async def get(self, id_: int) -> Any | None:
        """Return the OTP row for the given primary key, or ``None``."""

    @abstractmethod
    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: list[str] | None = None,
        **filters: Any,
    ) -> list[Any]:
        """Return an offset-paginated page of OTP rows."""

    @abstractmethod
    async def count(self, **filters: Any) -> int:
        """Return the number of OTP rows matching ``filters``."""

    @abstractmethod
    async def delete(self, id_: int) -> None:
        """Hard-delete the OTP row with the given primary key."""

    @abstractmethod
    async def get_or_create(self, phone: str) -> tuple[Any, bool]:
        """Return ``(otp_obj, created)`` for the given phone number.

        Args:
            phone: E.164 phone number to look up or create an OTP row for.

        Returns:
            Tuple of (OTP instance, created flag).
        """

    @abstractmethod
    async def get_by_phone(self, phone: str) -> Any | None:
        """Return the OTP row for the given phone, or ``None``.

        Args:
            phone: E.164 phone number.

        Returns:
            OTP instance, or ``None`` when not found.
        """

    @abstractmethod
    async def save(self, otp_obj: Any) -> None:
        """Persist changes to an existing OTP row.

        Args:
            otp_obj: OTP instance with mutations applied (e.g. after
                ``set_otp_and_validity``).
        """

    @abstractmethod
    async def delete_row(self, otp_obj: Any) -> None:
        """Hard-delete a resolved OTP row instance (single-use consume).

        Args:
            otp_obj: The OTP instance to delete.
        """
