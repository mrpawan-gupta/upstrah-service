"""Domain-layer base for immutable entity dataclasses.

Every domain entity in ``<app>/api/domain/entities/`` should subclass
:class:`BaseEntity` and decorate itself ``@dataclass(frozen=True)``.
Entities carry only the scalar attributes the use cases and presentation
layer need — ORM models never leak past the infrastructure layer.

:class:`BaseEntity` is itself a frozen dataclass, so every entity is a
dataclass by construction. It declares no fields, so it imposes no
ordering constraints on subclass fields; the subclass still applies its
own ``@dataclass(frozen=True)`` decorator to register its fields (and a
frozen base requires a frozen subclass, which the convention enforces).

Usage (in ``domain/entities/<entity>.py``)::

    from dataclasses import dataclass

    from common.api.base_entity import BaseEntity

    @dataclass(frozen=True)
    class UserEntity(BaseEntity):
        id: int
        email: str
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BaseEntity:
    """Frozen base for domain entity dataclasses.

    Provides a single shared helper, :meth:`to_dict`, so presentation
    mappers can serialise any entity without each entity re-implementing
    it. Subclasses must be declared ``@dataclass(frozen=True)``.
    """

    def to_dict(self) -> dict[str, Any]:
        """Serialise the entity to a plain ``dict`` for JSON responses.

        Returns:
            A recursively-expanded dict of the entity's fields (nested
            dataclass entities are expanded too).
        """
        return asdict(self)
