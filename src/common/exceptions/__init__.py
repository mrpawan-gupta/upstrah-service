"""Domain exception classes for the VMS application.

Re-exports the full exception hierarchy from
:mod:`common.exceptions.exceptions` so callers can import from this package
without referencing the inner module directly.

Exception → default HTTP status mapping:

* ``AppBaseError`` → 400
* ``RequirementNotMetError`` → 400
* ``ResourceNotFoundError`` → 404
* ``PermissionDeniedError`` → 403
* ``AuthenticationError`` → 401
* ``RateLimitError`` → 429
* ``DuplicateResourceError`` → 409
* ``ExternalServiceError`` → 502
* ``InternalServerError`` → 500
* ``DeprecationError`` → 410
"""

from common.exceptions.exceptions import (
    AppBaseError,
    AuthenticationError,
    DeprecationError,
    DuplicateResourceError,
    ExternalServiceError,
    InternalServerError,
    PermissionDeniedError,
    RateLimitError,
    RequirementNotMetError,
    ResourceNotFoundError,
)

__all__ = [
    "AppBaseError",
    "AuthenticationError",
    "DeprecationError",
    "DuplicateResourceError",
    "ExternalServiceError",
    "InternalServerError",
    "PermissionDeniedError",
    "RateLimitError",
    "RequirementNotMetError",
    "ResourceNotFoundError",
]
