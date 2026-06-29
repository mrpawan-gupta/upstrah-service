
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
user_token_var: ContextVar[str] = ContextVar("user_token", default="")
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)
company_ids_var: ContextVar[list[int] | None] = ContextVar("company_ids", default=None)


def set_correlation_id(value: str) -> None:
    """Bind a correlation ID to the current request context.

    Args:
        value: Correlation ID string to store (typically a UUID4 or
            a value propagated from an upstream ``X-Correlation-ID`` header).
    """
    correlation_id_var.set(value)


def get_correlation_id() -> str:
    """Return the correlation ID bound to the current request context.

    Returns:
        The stored correlation ID, or an empty string when called outside a
        request context.
    """
    return correlation_id_var.get()


def set_trace_id(value: str) -> None:
    """Bind a trace ID to the current request context.

    Args:
        value: Trace ID string to store (typically an 8-char hex token).
    """
    trace_id_var.set(value)


def set_request_id(value: str) -> None:
    """Bind a request ID to the current request context.

    Args:
        value: Request ID string to store (typically a UUID4).
    """
    request_id_var.set(value)


def get_trace_id() -> str:
    """Return the trace ID bound to the current request context.

    Returns:
        The stored trace ID, or an empty string when called outside a
        request context (e.g. in Celery tasks or tests).
    """
    return trace_id_var.get()


def get_request_id() -> str:
    """Return the request ID bound to the current request context.

    Returns:
        The stored request ID, or an empty string when called outside a
        request context.
    """
    return request_id_var.get()


def set_user_token(value: str) -> None:
    """Bind the raw JWT bearer token to the current request context.

    Args:
        value: The full bearer token string extracted from the Authorization header.
    """
    user_token_var.set(value)


def get_user_token() -> str:
    """Return the raw JWT bearer token bound to the current request context.

    Returns:
        The stored bearer token, or an empty string when called outside a
        request context.
    """
    return user_token_var.get()


def set_user_id(value: int | None) -> None:
    """Bind the authenticated user's ID to the current request context.

    Args:
        value: The integer user PK from the JWT payload, or ``None`` for
            unauthenticated requests.
    """
    user_id_var.set(value)


def get_user_id() -> int | None:
    """Return the authenticated user ID bound to the current request context.

    Returns:
        The integer user PK, or ``None`` when called outside a request context
        or for unauthenticated requests.
    """
    return user_id_var.get()


def set_company_ids(value: list[int]) -> None:
    """Bind the effective company IDs to the current request context.

    Args:
        value: List of integer company PKs resolved from the ``X-Company-IDs``
            header.  An empty list signals "all companies" (superuser with no
            header).
    """
    company_ids_var.set(value)


def get_company_ids() -> list[int]:
    """Return the effective company IDs bound to the current request context.

    Returns:
        List of integer company PKs, or an empty list when called outside a
        request context or when the superuser omitted the header.
    """
    return company_ids_var.get() or []
