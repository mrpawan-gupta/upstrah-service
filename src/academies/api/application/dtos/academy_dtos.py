"""Data Transfer Objects for the Academy application layer.

Defines the dataclass boundaries between the presentation layer and the
``Academy`` use-case facade. ``AcademyPatchDTO`` uses ``| None`` defaults
so a PATCH leaves unset fields unchanged; ``AcademyResponseDTO`` is the
read boundary serialised to the response.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from common.api import BaseModelDTO


@dataclass
class AcademyCreateDTO(BaseModelDTO):
    """Fields required to create an academy (POST).

    Attributes:
        name:        Display name.
        sport:       Primary sport trained.
        created_by:  PK of the owning user (resolved from the caller).
        description: Free-text description (defaults to empty).
        city:        City of operation (defaults to empty).
        status:      Lifecycle status (defaults to ``active``).
    """

    name: str
    sport: str
    created_by: int
    description: str = ""
    city: str = ""
    status: str = "active"


@dataclass
class AcademyUpdateDTO(BaseModelDTO):
    """Fields for a full replace of an academy (PUT) — all required.

    Attributes:
        name:        New display name.
        sport:       New primary sport.
        description: New description.
        city:        New city.
        status:      New lifecycle status.
    """

    name: str
    sport: str
    description: str
    city: str
    status: str


@dataclass
class AcademyPatchDTO(BaseModelDTO):
    """Fields for a partial update of an academy (PATCH).

    ``None`` means "leave unchanged".

    Attributes:
        name:        New display name, or ``None``.
        sport:       New primary sport, or ``None``.
        description: New description, or ``None``.
        city:        New city, or ``None``.
        status:      New lifecycle status, or ``None``.
    """

    name: str | None = None
    sport: str | None = None
    description: str | None = None
    city: str | None = None
    status: str | None = None


@dataclass
class AcademyResponseDTO(BaseModelDTO):
    """Read representation of an academy returned by use cases.

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

    id: int
    name: str
    sport: str
    description: str
    city: str
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
