"""Application-wide translatable message constants.

``Messages`` is a plain namespace class (no instances needed) that centralises
all user-visible strings used in exception defaults, API responses, and other
places where a short, translatable label is required.

All attributes are Django lazy-translated strings produced by
``gettext_lazy``.  ``Messages.DEFAULT`` is a ``dict`` mapping HTTP status
codes to their default short messages.
"""

from typing import ClassVar

from django.utils.translation import gettext_lazy as _


class Messages:
    """Namespace of translatable message constants used across the application.

    Every attribute is a Django ``Promise`` (lazy string) so that it is
    translated at render time rather than import time.

    Attributes:
        INTERNAL_SERVER_ERROR: Generic fallback for 5xx errors.
        AUTH_FAILED: Authentication failure.
        INVALID_TOKEN: JWT validation failure.
        TOKEN_EXPIRED: JWT expiry.
        TOKEN_REQUIRED: Missing bearer token.
        PERMISSION_DENIED: 403 default.
        RESOURCE_NOT_FOUND: 404 template; interpolate ``resource_type``.
        RESOURCE_CONFLICT: 409 default.
        INVALID_INPUT: 400 default for bad input.
        CONCURRENT_MODIFICATION: Optimistic-lock conflict.
        EXTERNAL_SERVICE_ERROR: 502 template; interpolate ``service_name``.
        SERVICE_UNAVAILABLE: 503 default.
        NETWORK_ERROR: Generic network failure.
        CONNECTION_TIMEOUT: Timeout default.
        RATE_LIMIT_EXCEEDED: 429 default.
        RATE_LIMIT_RETRY: 429 with retry hint; interpolate ``retry_after``.
        ENDPOINT_DEPRECATED: 410 gone.
        SUCCESSFUL: Generic 2xx success.
        CREATED: Resource created (201).
        UPDATED: Resource updated (200).
        DELETED: Resource deleted (200/204).
        DEFAULT: Mapping of HTTP status codes to short messages.
    """

    INTERNAL_SERVER_ERROR = _(
        "An unexpected error occurred. Please try again or contact support."
    )

    # Authentication & Authorization
    AUTH_FAILED = _(
        "Authentication failed. Please check your credentials and try again."
    )
    INVALID_TOKEN = _("Your authentication token is invalid. Please log in again.")
    TOKEN_EXPIRED = _("Your authentication token has expired. Please log in again.")
    TOKEN_REQUIRED = _("Authentication is required. Please provide a valid token.")
    PERMISSION_DENIED = _("You do not have permission to perform this action.")

    # Resource errors
    RESOURCE_NOT_FOUND = _("The requested {resource_type} could not be found.")
    RESOURCE_CONFLICT = _("A record with these details already exists.")
    INVALID_INPUT = _(
        "The provided input is invalid. Please review your request and try again."
    )

    # Concurrency errors
    CONCURRENT_MODIFICATION = _(
        "This record was modified by another user. Please refresh and try again."
    )

    # External service errors
    EXTERNAL_SERVICE_ERROR = _(
        "The {service_name} service is temporarily unavailable. Please try again later."
    )
    SERVICE_UNAVAILABLE = _(
        "An external service is temporarily unavailable. Please try again later."
    )
    NETWORK_ERROR = _(
        "A network error occurred. Please check your connection and try again."
    )
    CONNECTION_TIMEOUT = _("The request timed out. Please try again.")

    # Rate limiting
    RATE_LIMIT_EXCEEDED = _("Too many requests. Please wait a moment and try again.")
    RATE_LIMIT_RETRY = _("Too many requests. Please retry after {retry_after} seconds.")

    # Deprecation
    ENDPOINT_DEPRECATED = _("This endpoint is no longer available.")

    # Success messages
    SUCCESSFUL = _("Request completed successfully.")
    CREATED = _("Record created successfully.")
    UPDATED = _("Record updated successfully.")
    DELETED = _("Record deleted successfully.")

    DEFAULT: ClassVar = {
        200: _("Fetched"),
        201: _("Created"),
        202: _("Accepted"),
        204: _("No Content"),
        400: _("Bad Request"),
        401: _("Unauthorized"),
        403: _("Forbidden"),
        404: _("Not Found"),
        405: _("Method Not Allowed"),
        409: _("Conflict"),
        422: _("Unprocessable Entity"),
        429: _("Too Many Requests"),
        500: _("Internal Server Error"),
        501: _("Not Implemented"),
        502: _("Bad Gateway"),
        503: _("Service Unavailable"),
    }
