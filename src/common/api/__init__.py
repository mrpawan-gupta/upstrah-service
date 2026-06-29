"""Common API utilities and shared clean-arch base classes.

Re-exports the three-layer CRUD base classes (``BaseController``,
``BaseUseCase``, ``BaseRepository``), the per-layer building-block bases
(``BaseEntity``, ``BaseModelDTO``, ``BaseRequestSchema``,
``BaseResponseSchema``, ``BaseFilter``), and the standard HTTP response
envelope helpers so every service imports the shared contracts from
one place.
"""

from common.api.base_controller import BaseController
from common.api.base_entity import BaseEntity
from common.api.base_filter import BaseFilter
from common.api.base_model_dto import BaseModelDTO
from common.api.base_repository import BaseRepository
from common.api.base_request_schema import BaseRequestSchema
from common.api.base_response_schema import BaseResponseSchema
from common.api.base_use_case import BaseUseCase
from common.api.response import (
    APIResponse,
    OffsetPaginatedResponse,
)

__all__ = [
    "APIResponse",
    "BaseController",
    "BaseEntity",
    "BaseFilter",
    "BaseModelDTO",
    "BaseRepository",
    "BaseRequestSchema",
    "BaseResponseSchema",
    "BaseUseCase",
    "OffsetPaginatedResponse",
]
