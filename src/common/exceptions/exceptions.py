"""Domain exception hierarchy for the VMS application.

All exceptions that should produce a deterministic HTTP response inherit from
:class:`AppBaseError`.  The universal exception handler in
``common.exceptions.exception_handler`` converts these exceptions to JSON
envelopes automatically.

Exception → default HTTP status mapping:

+---------------------------+--------+
| Exception class           | Status |
+===========================+========+
| AppBaseError              | 400    |
| RequirementNotMetError    | 400    |
| ResourceNotFoundError     | 404    |
| PermissionDeniedError     | 403    |
| AuthenticationError       | 401    |
| RateLimitError            | 429    |
| DuplicateResourceError    | 409    |
| ExternalServiceError      | 502    |
| InternalServerError       | 500    |
| DeprecationError          | 410    |
+---------------------------+--------+
"""

from starlette import status

from common.constants import Messages


class AppBaseError(Exception):
    """Base exception for all application-domain errors.

    Carries both a human-readable ``message`` (forwarded to the client) and
    an HTTP ``status_code`` used by the universal exception handler.

    Attributes:
        message: User-facing error description.
        status_code: HTTP status code to return.
    """

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        """Initialise with a message and optional HTTP status code.

        Args:
            message: Human-readable error description sent to the client.
            status_code: HTTP status code (default 400 Bad Request).
        """
        self.message = message
        self.status_code = status_code


class DeprecationError(AppBaseError):
    """Raised when a requested resource or endpoint is deprecated and no longer available."""

    def __init__(
        self,
        message: str | None = None,
        status_code: int = status.HTTP_410_GONE,
    ):
        """Initialise deprecation error.

        Args:
            message: Error message; defaults to ``Messages.ENDPOINT_DEPRECATED``.
            status_code: HTTP status code (default 410 Gone).
        """
        if message is None:
            message = Messages.ENDPOINT_DEPRECATED
        super().__init__(message, status_code)


class RequirementNotMetError(AppBaseError):
    """Raised when required information or parameters are missing from a request."""

    def __init__(
        self, message: str | None = None, status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        """Initialise requirement not met error.

        Args:
            message: Error message; defaults to ``Messages.INVALID_INPUT``.
            status_code: HTTP status code (default 400 Bad Request).
        """
        if message is None:
            message = Messages.INVALID_INPUT
        super().__init__(message, status_code)


class ResourceNotFoundError(AppBaseError):
    """Raised when a requested resource cannot be found."""

    def __init__(
        self, message: str | None = None, status_code: int = status.HTTP_404_NOT_FOUND
    ):
        """Initialise resource not found error.

        Args:
            message: Error message; defaults to ``Messages.RESOURCE_NOT_FOUND``.
            status_code: HTTP status code (default 404 Not Found).
        """
        if message is None:
            message = Messages.RESOURCE_NOT_FOUND
        super().__init__(message, status_code)


class ExternalServiceError(AppBaseError):
    """Raised when an external service call fails."""

    def __init__(
        self,
        message: str | None = None,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
    ):
        """Initialise an external service error.

        Args:
            message: Human-readable error description; defaults to
                ``Messages.SERVICE_UNAVAILABLE``.
            status_code: HTTP status code (default 502 Bad Gateway).
        """
        if message is None:
            message = Messages.SERVICE_UNAVAILABLE
        super().__init__(message, status_code)


class InternalServerError(AppBaseError):
    """Raised when an internal server error occurs."""

    def __init__(
        self,
        message: str | None = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        """Initialise an internal server error.

        Args:
            message: Human-readable error description; defaults to
                ``Messages.INTERNAL_SERVER_ERROR``.
            status_code: HTTP status code (default 500 Internal Server Error).
        """
        if message is None:
            message = Messages.INTERNAL_SERVER_ERROR
        super().__init__(message, status_code)


class PermissionDeniedError(AppBaseError):
    """Raised when access to a resource is denied due to insufficient permissions."""

    def __init__(
        self, message: str | None = None, status_code: int = status.HTTP_403_FORBIDDEN
    ):
        """Initialise permission denied error.

        Args:
            message: Error message; defaults to ``Messages.PERMISSION_DENIED``.
            status_code: HTTP status code (default 403 Forbidden).
        """
        if message is None:
            message = Messages.PERMISSION_DENIED
        super().__init__(message, status_code)


class RateLimitError(AppBaseError):
    """Raised when the rate limit is exceeded."""

    def __init__(
        self,
        message: str | None = None,
        status_code: int = status.HTTP_429_TOO_MANY_REQUESTS,
    ):
        """Initialise a rate limit error.

        Args:
            message: Human-readable error description; defaults to
                ``Messages.RATE_LIMIT_EXCEEDED``.
            status_code: HTTP status code (default 429 Too Many Requests).
        """
        if message is None:
            message = Messages.RATE_LIMIT_EXCEEDED
        super().__init__(message, status_code)


class AuthenticationError(AppBaseError):
    """Raised when authentication fails or credentials are invalid."""

    def __init__(
        self,
        message: str | None = None,
        status_code: int = status.HTTP_401_UNAUTHORIZED,
    ):
        """Initialise authentication error.

        Args:
            message: Error message; defaults to ``Messages.AUTH_FAILED``.
            status_code: HTTP status code (default 401 Unauthorized).
        """
        if message is None:
            message = Messages.AUTH_FAILED
        super().__init__(message, status_code)


class DuplicateResourceError(AppBaseError):
    """Raised when a create/update violates a unique constraint."""

    def __init__(
        self,
        message: str | None = None,
        status_code: int = status.HTTP_409_CONFLICT,
    ):
        """Initialise a duplicate resource error.

        Args:
            message: Human-readable error description; defaults to
                ``Messages.RESOURCE_CONFLICT``.  Override to name the
                specific field or resource that caused the collision.
            status_code: HTTP status code (default 409 Conflict).
        """
        if message is None:
            message = Messages.RESOURCE_CONFLICT
        super().__init__(message, status_code)
