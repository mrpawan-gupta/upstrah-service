"""Application-layer base for Data Transfer Object dataclasses.

DTOs carry the minimal set of fields each use-case boundary needs
between the presentation and domain layers. They hold no validation
logic — that belongs to the Pydantic request schemas at the HTTP edge.

Every DTO in ``<app>/api/application/dtos/`` should subclass
:class:`BaseModelDTO` and decorate itself ``@dataclass``.

Usage (in ``application/dtos/<entity>_dtos.py``)::

    from dataclasses import dataclass

    from common.api.base_model_dto import BaseModelDTO

    @dataclass
    class UserCreateDTO(BaseModelDTO):
        email: str
        phone: str
        first_name: str = ""

The base declares no fields, so it imposes no ordering constraints on
subclass fields, and is intentionally not decorated with ``@dataclass``
— the subclass owns that decoration. DTOs are mutable by convention
(unlike frozen :class:`common.api.base_entity.BaseEntity`).
"""

from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
from typing import Any, TypeVar

T = TypeVar("T", bound="BaseModelDTO")


class BaseModelDTO:
    """Base for application-layer DTO dataclasses.

    Provides :meth:`to_dict` / :meth:`from_dict` so use cases and mappers
    can serialise a DTO to ORM ``**fields`` and rebuild one from a loose
    dict (e.g. an external provider / router payload) without
    re-implementing it per DTO. Subclasses must be declared ``@dataclass``.
    """

    def to_dict(self) -> dict[str, Any]:
        """Serialise the DTO to a plain ``dict``.

        Returns:
            A recursively-expanded dict of the DTO's fields.

        Raises:
            TypeError: If the subclass is not a dataclass.
        """
        if not is_dataclass(self):
            raise TypeError(
                f"{type(self).__name__} must be a @dataclass to call to_dict()"
            )
        return asdict(self)

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """Build a DTO from a loose dict, ignoring unknown keys.

        Mirrors Pydantic ``extra="ignore"`` so a permissive external
        payload (retriever hit, router result) can be projected onto the
        DTO without raising on keys the dataclass does not declare.
        Missing required fields still raise ``TypeError``, exactly as a
        direct constructor call would.

        Args:
            data: Source mapping; keys not matching a field are dropped.

        Raises:
            TypeError: If the subclass is not a dataclass.
        """
        if not is_dataclass(cls):
            raise TypeError(f"{cls.__name__} must be a @dataclass to call from_dict()")
        field_names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in field_names})
