"""Pydantic request/response schemas for the Academy endpoints.

Covers ``POST/GET /academies`` and ``GET/PUT/PATCH/DELETE
/academies/{id}``. The PUT schema makes every mutable field required; the
PATCH schema makes every field ``| None = None`` (unset = leave unchanged).
``status`` is validated against the model choices here, never in the
controller.
"""

from __future__ import annotations

from datetime import datetime

from django.utils.translation import gettext_lazy as _
from pydantic import Field, field_validator

from academies.constants import AcademyStatus
from common.api import BaseRequestSchema, BaseResponseSchema

_STATUS_VALUES = {c.value for c in AcademyStatus}


def _validate_status(value: str | None) -> str | None:
    """Return ``value`` when it is a valid status, else raise ``ValueError``."""
    if value is not None and value not in _STATUS_VALUES:
        raise ValueError(
            str(_("status must be one of: {choices}.")).format(
                choices=", ".join(sorted(_STATUS_VALUES))
            )
        )
    return value


class AcademyCreateSchema(BaseRequestSchema):
    """Request body for ``POST /academies``.

    Attributes:
        name:        Display name.
        sport:       Primary sport trained.
        description: Optional free-text description.
        city:        Optional city of operation.
        status:      Lifecycle status (defaults to ``active``).
    """

    name: str = Field(..., min_length=1, max_length=255, description=str(_("Name.")))
    sport: str = Field(
        ..., min_length=1, max_length=100, description=str(_("Primary sport."))
    )
    description: str = Field("", description=str(_("Free-text description.")))
    city: str = Field("", max_length=120, description=str(_("City of operation.")))
    status: str = Field(
        AcademyStatus.ACTIVE.value, description=str(_("'active' or 'inactive'."))
    )

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate that status is an accepted lifecycle value."""
        return _validate_status(v)


class AcademyUpdateSchema(BaseRequestSchema):
    """Request body for ``PUT /academies/{id}`` — full replace (all required).

    Attributes:
        name:        New display name.
        sport:       New primary sport.
        description: New description.
        city:        New city.
        status:      New lifecycle status.
    """

    name: str = Field(..., min_length=1, max_length=255, description=str(_("Name.")))
    sport: str = Field(
        ..., min_length=1, max_length=100, description=str(_("Primary sport."))
    )
    description: str = Field(..., description=str(_("Free-text description.")))
    city: str = Field(..., max_length=120, description=str(_("City of operation.")))
    status: str = Field(..., description=str(_("'active' or 'inactive'.")))

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate that status is an accepted lifecycle value."""
        return _validate_status(v)


class AcademyPatchSchema(BaseRequestSchema):
    """Request body for ``PATCH /academies/{id}`` — all fields optional.

    Unset fields are left unchanged.

    Attributes:
        name:        New display name, or ``null``.
        sport:       New primary sport, or ``null``.
        description: New description, or ``null``.
        city:        New city, or ``null``.
        status:      New lifecycle status, or ``null``.
    """

    name: str | None = Field(
        None, min_length=1, max_length=255, description=str(_("Name."))
    )
    sport: str | None = Field(
        None, min_length=1, max_length=100, description=str(_("Primary sport."))
    )
    description: str | None = Field(None, description=str(_("Free-text description.")))
    city: str | None = Field(
        None, max_length=120, description=str(_("City of operation."))
    )
    status: str | None = Field(None, description=str(_("'active' or 'inactive'.")))

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate that status is an accepted lifecycle value."""
        return _validate_status(v)


class AcademyResponseSchema(BaseResponseSchema):
    """Response shape for an academy.

    Attributes:
        id:          Primary key.
        name:        Display name.
        sport:       Primary sport trained.
        description: Free-text description.
        city:        City of operation.
        status:      Lifecycle status.
        created_by:  PK of the owning user.
        created_at:  Row creation timestamp.
        updated_at:  Row last-modified timestamp.
    """

    id: int = Field(..., description=str(_("Primary key.")))
    name: str = Field(..., description=str(_("Display name.")))
    sport: str = Field(..., description=str(_("Primary sport.")))
    description: str = Field(..., description=str(_("Free-text description.")))
    city: str = Field(..., description=str(_("City of operation.")))
    status: str = Field(..., description=str(_("Lifecycle status.")))
    created_by: int = Field(..., description=str(_("PK of the owning user.")))
    created_at: datetime = Field(..., description=str(_("Creation timestamp.")))
    updated_at: datetime = Field(..., description=str(_("Last-modified timestamp.")))
