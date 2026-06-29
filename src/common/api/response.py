"""Standardised API response Pydantic envelope models."""

from typing import Any, TypeVar

from django.utils.encoding import force_str
from django.utils.functional import Promise
from pydantic import BaseModel, Field, model_validator

from common.constants import Messages

DataT = TypeVar("DataT")


class OffsetPaginatedResponse(BaseModel):
    """Pagination metadata attached to list endpoint responses.

    Attributes:
        limit: Maximum number of records requested.
        offset: Number of records skipped before this page.
        total: Total number of matching records in the database.
        returned: Number of records included in the current response.
        has_more: ``True`` when more records exist beyond this page.
    """

    limit: int
    offset: int
    total: int
    returned: int
    has_more: bool


class APIResponse[DataT](BaseModel):
    """Standardised API response envelope used as the FastAPI ``response_model``.

    Attributes:
        data: Response payload; defaults to an empty dict.
        message: Human-readable status message.
        status: HTTP status code (also drives ``success``).
        success: ``True`` when ``status`` is in the 2xx range.
        meta: Optional pagination metadata for list endpoints.
    """

    data: DataT | None = None
    message: str = Field(default="", description="Response message")
    status: int = Field(default=200, description="Response status code")
    success: bool = Field(default=True)
    meta: OffsetPaginatedResponse | None = None

    @model_validator(mode="after")
    def set_default_data(self) -> "APIResponse[DataT]":
        """Set ``success`` and default ``message`` / ``data`` after validation."""
        self.success = 200 <= self.status < 300

        if not self.message:
            self.message = force_str(
                Messages.DEFAULT.get(
                    self.status,
                    (
                        Messages.SUCCESSFUL
                        if self.success
                        else Messages.INTERNAL_SERVER_ERROR
                    ),
                )
            )

        if self.data is None:
            self.data = {}  # type: ignore

        return self

    @model_validator(mode="before")
    @classmethod
    def convert_promises(cls, input_data: Any) -> Any:
        """Force-evaluate Django lazy-string ``Promise`` objects to plain strings.

        Args:
            input_data: Raw input dict passed to the model constructor.

        Returns:
            The same dict with ``message`` / ``error`` values coerced to ``str``.
        """
        if isinstance(input_data, dict):
            for key in ["message", "error"]:
                if isinstance(input_data.get(key), Promise):
                    input_data[key] = force_str(input_data[key])
        return input_data
