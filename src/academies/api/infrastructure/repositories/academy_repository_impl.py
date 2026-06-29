"""Django-ORM implementation of :class:`IAcademyRepository`.

Backs the contract with the ``academies.models.Academy`` model. Inherits
the shared async CRUD surface from :class:`common.api.BaseRepository`
(``get`` / ``create`` / ``update`` / ``partial_update`` / ``delete`` /
``list`` / ``count`` return raw ORM rows; mapping to entities is the use
case's job). Sets ``model`` and ``default_ordering``. Data access only.
"""

from __future__ import annotations

from academies.api.domain.repositories.academy_repository import IAcademyRepository
from academies.models import Academy
from common.api import BaseRepository


class AcademyRepositoryImpl(BaseRepository, IAcademyRepository):
    """Concrete Academy repository over ``academies.models.Academy``.

    Attributes:
        model:            The :class:`academies.models.Academy` ORM model.
        default_ordering: Default ``order_by`` for ``list`` queries.
    """

    model = Academy
    default_ordering = ["-created_at"]
