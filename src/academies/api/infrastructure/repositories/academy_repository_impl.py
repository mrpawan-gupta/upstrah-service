"""Django-ORM implementation of :class:`IAcademyRepository`.

Backs the contract with the ``academies.models.Academy`` model. Inherits
the shared async CRUD surface from :class:`common.api.BaseRepository` and
overrides ``get`` / ``list`` to ``prefetch_related("sports")`` so the
mapper can read the M2M without a per-row query. Adds ``existing_sport_ids``
(validation support) and ``set_sports`` (assign the M2M on a saved row).
Data access only.
"""

from __future__ import annotations

from typing import Any

from academies.api.domain.repositories.academy_repository import IAcademyRepository
from academies.models import Academy, Sport
from common.api import BaseRepository


class AcademyRepositoryImpl(BaseRepository, IAcademyRepository):
    """Concrete Academy repository over ``academies.models.Academy``.

    Attributes:
        model:            The :class:`academies.models.Academy` ORM model.
        default_ordering: Default ``order_by`` for ``list`` queries.
    """

    model = Academy
    default_ordering = ["-created_at"]

    async def get(self, id_: int) -> Academy | None:
        """Return the academy (with sports prefetched) for ``id_``, or ``None``."""
        try:
            return await Academy.objects.prefetch_related("sports").aget(pk=id_)
        except Academy.DoesNotExist:
            return None

    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: list[str] | None = None,
        **filters: Any,
    ) -> list[Academy]:
        """Return an offset-paginated page of academies with sports prefetched."""
        qs = Academy.objects.filter(**filters).prefetch_related("sports")
        ordering = order_by or self.default_ordering
        if ordering:
            qs = qs.order_by(*ordering)
        qs = qs[offset : offset + limit]
        return [obj async for obj in qs]

    async def existing_sport_ids(self, sport_ids: list[int]) -> set[int]:
        """Return the subset of ``sport_ids`` that exist as ``Sport`` rows."""
        if not sport_ids:
            return set()
        return {
            pk
            async for pk in Sport.objects.filter(pk__in=sport_ids).values_list(
                "pk", flat=True
            )
        }

    async def set_sports(self, id_: int, sport_ids: list[int]) -> Academy:
        """Replace the academy's sports M2M with ``sport_ids`` and return the row.

        The instance must already be saved (M2M assignment requires a PK).
        Re-fetches with ``sports`` prefetched so the mapper sees the new set.
        """
        academy = await Academy.objects.aget(pk=id_)
        await academy.sports.aset(sport_ids)
        return await Academy.objects.prefetch_related("sports").aget(pk=id_)
