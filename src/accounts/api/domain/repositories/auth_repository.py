"""Abstract repository interface for authentication operations.

Pure ``abc.ABC`` with no Django import — the concrete implementation in
the infrastructure layer satisfies this contract using the Django ORM.
Methods return raw ``User`` ORM instances (typed via ``TYPE_CHECKING``
only) because the auth use case needs the live row to mint token claims;
no ORM object is exposed past the use case.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from accounts.models import User


class IAuthRepository(ABC):
    """Contract that all auth repository implementations must satisfy."""

    @abstractmethod
    async def get_user_by_id(self, user_id: int | str) -> User | None:
        """Return the ``User`` with the given PK, or ``None`` if not found.

        Args:
            user_id: Primary key of the user to retrieve.

        Returns:
            Matching ``User`` instance, or ``None``.
        """

    @abstractmethod
    async def get_or_create_user_by_phone(
        self, phone: str
    ) -> tuple[User, bool]:
        """Return ``(user, created)`` for the given phone number.

        Resolves an existing user via the ``PhoneNumber`` table or the
        ``User.phone`` convenience column, creating a new phone-only user
        (and verified ``PhoneNumber`` row) when none exists.

        Args:
            phone: E.164 phone number that completed an OTP challenge.

        Returns:
            Tuple of (``User`` instance, created flag).
        """

    @abstractmethod
    async def get_user_token_claims(self, user_id: int | str) -> dict[str, Any]:
        """Build the JWT ``user_data`` payload for ``user_id``.

        Args:
            user_id: PK of the user.

        Returns:
            Dict with ``is_superuser``, ``is_staff``, ``roles`` (list[str]),
            and ``scopes`` (list[str]) — ready to pass straight to
            ``jwt_handler.generate_access_token``.
        """
