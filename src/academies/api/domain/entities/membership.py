"""Domain entity for the Membership aggregate.

Immutable scalar representation of an :class:`academies.models.Membership`
row. Carries the apply → pending → approved/rejected state plus the owning
user and academy identifiers; no ORM object leaks past infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from common.api import BaseEntity


@dataclass(frozen=True)
class MembershipEntity(BaseEntity):
    """Immutable domain representation of a ``Membership`` row.

    Attributes:
        id:         Primary key.
        user_id:    PK of the applying user.
        academy_id: PK of the academy applied to.
        role:       Requested role (head/coach/admin/staff/athlete).
        status:     ``"pending"``, ``"approved"``, or ``"rejected"``.
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
