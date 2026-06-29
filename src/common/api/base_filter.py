"""Pydantic base class for list-endpoint filter schemas.

Usage (in ``presentation/schemas/<entity>_schemas.py``)::

    from common.api.base_filter import BaseFilter

    class ClaimFilter(BaseFilter):
        state: str | None = None
        severity: str | None = None

Usage (in ``api/v1/<entity>_endpoints.py``)::

    @router.get("/claims")
    async def list_claims(
        filter: ClaimFilter = Depends(),
        company_ids: list[int] = Depends(get_company_ids),
        controller: ClaimController = Depends(get_claim_controller),
    ) -> APIResponse:
        items, meta = await controller.list(filter=filter, company_ids=company_ids)
        ...

Rules:
- ``company_ids`` is always injected from ``X-Company-IDs`` header via
  ``get_company_ids`` — never add it as a filter field.
- Override ``to_orm_filters()`` in a subclass when a field name differs from
  the Django ORM lookup keyword (e.g. ``action_code`` → ``action__code``).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BaseFilter(BaseModel):
    """Base filter schema for list endpoints.

    Pagination fields (``limit``, ``offset``) and sorting / search fields
    (``search``, ``sort_by``, ``sort_order``) are excluded from
    ``to_orm_filters()`` — pass them directly to the use case.
    """

    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    search: str | None = None
    sort_by: str | None = None
    sort_order: str | None = Field(default=None, pattern="^(asc|desc)$")

    _EXCLUDED = frozenset({"limit", "offset", "search", "sort_by", "sort_order"})

    def to_orm_filters(self) -> dict[str, Any]:
        """Return a ``{field: value}`` dict for ORM ``.filter(**kwargs)``.

        Excludes pagination/sorting/search fields and any field whose value is
        ``None``.  Subclasses may override to rename keys (e.g. FK traversals
        like ``action__code``).
        """
        return {
            k: v
            for k, v in self.model_dump().items()
            if k not in self._EXCLUDED and v is not None
        }

    def to_order_by(self) -> list[str] | None:
        """Return the ORM ``order_by`` list derived from the sort fields.

        Maps ``sort_by`` / ``sort_order`` to a single-element ``.order_by()``
        argument list, prefixing the field with ``-`` for descending order.
        Returns ``None`` when no ``sort_by`` is supplied so the caller falls
        back to the repository's ``default_ordering``.
        """
        if not self.sort_by:
            return None
        prefix = "-" if self.sort_order == "desc" else ""
        return [f"{prefix}{self.sort_by}"]
