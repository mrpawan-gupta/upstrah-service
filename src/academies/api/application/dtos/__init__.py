"""Data Transfer Objects for the academies application layer.

Dataclass boundaries between the presentation layer and the use cases for
the academy and membership aggregates. Each extends
:class:`common.api.BaseModelDTO`; patch DTOs use ``| None`` defaults so a
PATCH leaves unset fields unchanged.
"""

from academies.api.application.dtos.academy_dtos import (
    AcademyCreateDTO,
    AcademyPatchDTO,
    AcademyResponseDTO,
    AcademyUpdateDTO,
)
from academies.api.application.dtos.membership_dtos import (
    MembershipCreateDTO,
    MembershipResponseDTO,
)

__all__ = [
    "AcademyCreateDTO",
    "AcademyPatchDTO",
    "AcademyResponseDTO",
    "AcademyUpdateDTO",
    "MembershipCreateDTO",
    "MembershipResponseDTO",
]
