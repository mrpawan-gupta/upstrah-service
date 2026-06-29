"""Domain entity for the authentication token aggregate.

``AuthTokenEntity`` is a pure, frozen dataclass carrying the issued JWT
access/refresh token pair. It depends on nothing outside the standard
library — no Django, FastAPI, or Pydantic — so the domain layer stays
framework-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthTokenEntity:
    """Immutable representation of an issued JWT access/refresh token pair.

    Attributes:
        access_token:  Short-lived RS256 access JWT.
        refresh_token: Long-lived RS256 refresh JWT used for rotation.
        token_type:    Authorization-header token type; always ``"bearer"``.
    """

    access_token: str
    refresh_token: str
    token_type: str = field(default="bearer")
