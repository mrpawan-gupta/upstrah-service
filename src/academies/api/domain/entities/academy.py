"""Domain entity for the Academy aggregate.

Immutable scalar representation of an :class:`academies.models.Academy`
row. ORM models never escape the infrastructure layer; this frozen entity
carries only the fields the use cases and presentation layer need.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from common.api import BaseEntity


@dataclass(frozen=True)
class AcademyEntity(BaseEntity):
    """Immutable domain representation of an ``Academy`` row.

    Attributes:
        id:          Primary key.
        name:        Display name.
        sport:       Primary sport trained.
        description: Free-text description (may be empty).
        city:        City of operation (may be empty).
        status:      ``"active"`` or ``"inactive"``.
        created_by:  PK of the owning user.
        created_at:  Row creation timestamp.
        updated_at:  Row last-modified timestamp.
    """

    id: int
    name: str
    sport: str
    description: str
    city: str
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
