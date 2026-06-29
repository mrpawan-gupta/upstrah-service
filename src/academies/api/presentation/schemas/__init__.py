"""Pydantic request/response schemas for the academies endpoints.

Request schemas extend :class:`common.api.BaseRequestSchema`
(``extra="forbid"``); response schemas extend
:class:`common.api.BaseResponseSchema` (``from_attributes=True``). PUT
schemas are all-required; PATCH schemas are all-optional. Validation lives
here, never in the controller.
"""

from academies.api.presentation.schemas.academy_schemas import (
    AcademyCreateSchema,
    AcademyPatchSchema,
    AcademyResponseSchema,
    AcademyUpdateSchema,
)
from academies.api.presentation.schemas.membership_schemas import (
    MembershipCreateSchema,
    MembershipResponseSchema,
)

__all__ = [
    "AcademyCreateSchema",
    "AcademyPatchSchema",
    "AcademyResponseSchema",
    "AcademyUpdateSchema",
    "MembershipCreateSchema",
    "MembershipResponseSchema",
]
