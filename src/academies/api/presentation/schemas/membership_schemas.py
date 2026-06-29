"""Pydantic request/response schemas for the Membership endpoints.

Covers ``POST/GET /academies/{academy_id}/memberships`` and the
``POST /memberships/{id}/approve|reject`` transitions. The create schema
carries only the requested ``role`` (the applying user comes from the
token, the academy from the path, and ``status`` is server-assigned to
``pending``). ``role`` is validated against the model choices here.
"""

from __future__ import annotations

from datetime import datetime

from django.utils.translation import gettext_lazy as _
from pydantic import Field, field_validator

from academies.constants import MembershipRole
from common.api import BaseRequestSchema, BaseResponseSchema

_ROLE_VALUES = {c.value for c in MembershipRole}


class MembershipCreateSchema(BaseRequestSchema):
    """Request body for ``POST /academies/{academy_id}/memberships``.

    Attributes:
        role: Requested role (head/coach/admin/staff/athlete).
    """

    role: str = Field(
        ..., description=str(_("Requested role: head/coach/admin/staff/athlete."))
    )

    @field_validator("role", mode="after")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate that role is one of the accepted membership roles."""
        if v not in _ROLE_VALUES:
            raise ValueError(
                str(_("role must be one of: {choices}.")).format(
                    choices=", ".join(sorted(_ROLE_VALUES))
                )
            )
        return v


class MembershipResponseSchema(BaseResponseSchema):
    """Response shape for a membership.

    Attributes:
        id:         Primary key.
        user_id:    PK of the applying user.
        academy_id: PK of the academy applied to.
        role:       Requested role.
        status:     ``pending``, ``approved``, or ``rejected``.
        created_at: Row creation timestamp.
        updated_at: Row last-modified timestamp.
    """

    id: int = Field(..., description=str(_("Primary key.")))
    user_id: int = Field(..., description=str(_("PK of the applying user.")))
    academy_id: int = Field(..., description=str(_("PK of the academy.")))
    role: str = Field(..., description=str(_("Requested role.")))
    status: str = Field(..., description=str(_("Approval status.")))
    created_at: datetime = Field(..., description=str(_("Creation timestamp.")))
    updated_at: datetime = Field(..., description=str(_("Last-modified timestamp.")))
