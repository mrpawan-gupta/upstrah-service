"""Data Transfer Objects for the Membership application layer.

Defines the dataclass boundaries between the presentation layer and the
``Membership`` use-case facade. ``MembershipCreateDTO`` carries an
application (status is server-assigned to ``pending``);
``MembershipResponseDTO`` is the read boundary serialised to the response.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from common.api import BaseModelDTO


@dataclass
class MembershipCreateDTO(BaseModelDTO):
    """Fields required to apply for a membership (POST).

    Status is not carried here — the use case assigns ``pending``.

    Attributes:
        user_id:    PK of the applying user (resolved from the caller).
        academy_id: PK of the academy applied to (from the path).
        role:       Requested role (head/coach/admin/staff/athlete).
    """

    user_id: int
    academy_id: int
    role: str


@dataclass
class MembershipResponseDTO(BaseModelDTO):
    """Read representation of a membership returned by use cases.

    Attributes:
        id:         Primary key.
        user_id:    PK of the applying user.
        academy_id: PK of the academy applied to.
        role:       Requested role.
        status:     ``pending``, ``approved``, or ``rejected``.
        created_at: Row creation timestamp.
        updated_at: Row last-modified timestamp.
    """

    id: int
    user_id: int
    academy_id: int
    role: str
    status: str
    created_at: datetime
    updated_at: datetime
