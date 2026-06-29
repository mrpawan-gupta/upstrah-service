"""Presentation-layer base for outbound response Pydantic schemas.

Response schemas are the wire shape returned inside the ``data`` block
of :class:`common.api.response.APIResponse`. :class:`BaseResponseSchema`
pins ``from_attributes=True`` so a mapper can build the schema straight
from a domain entity (or ORM instance) with
``UserResponseSchema.model_validate(entity)`` without first converting
to a dict.

Usage (in ``presentation/schemas/<entity>_schemas.py``)::

    from pydantic import Field

    from common.api.base_response_schema import BaseResponseSchema

    class UserResponseSchema(BaseResponseSchema):
        id: int = Field(..., description="Primary key.")
        email: str = Field(..., description="Login email address.")
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseResponseSchema(BaseModel):
    """Base for outbound response Pydantic schemas.

    ``from_attributes=True`` lets mappers validate the schema directly
    from a frozen entity or ORM instance via ``model_validate(obj)``.
    """

    model_config = ConfigDict(from_attributes=True)
