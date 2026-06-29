"""Presentation-layer base for inbound request Pydantic schemas.

Request schemas validate the HTTP request body / query string at the
edge before the controller builds a DTO. :class:`BaseRequestSchema`
pins ``extra="forbid"`` so unknown fields are rejected with a 422
rather than silently ignored — a caller that misspells a field hears
about it instead of having the value dropped.

Usage (in ``presentation/schemas/<entity>_schemas.py``)::

    from pydantic import Field

    from common.api.base_request_schema import BaseRequestSchema

    class UserRequestSchema(BaseRequestSchema):
        email: EmailStr = Field(..., description="Login email address.")
        password: str = Field(..., min_length=8)

For paginated list query strings use
:class:`common.api.base_filter.BaseFilter` instead — it adds the
``limit`` / ``offset`` / ``search`` / ``sort_*`` fields and the
``to_orm_filters()`` helper.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseRequestSchema(BaseModel):
    """Base for inbound request body / query Pydantic schemas.

    ``extra="forbid"`` rejects unknown fields so typos surface as a 422
    instead of being silently discarded.
    """

    model_config = ConfigDict(extra="forbid")
