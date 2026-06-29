"""HTTP request/response logging middleware for Django and FastAPI.

Both middleware classes emit the same structlog events with identical keys so
that log aggregation pipelines see a uniform schema regardless of which stack
handled the request:

* ``request_started``   — logged before the handler runs
* ``request_finished``  — logged after the response, includes ``status_code`` / ``duration_ms``
* ``request_exception`` — logged when an unhandled exception escapes the handler

Classes:
    DjangoRequestLoggingMiddleware: Callable Django middleware.
    FastAPIRequestLoggingMiddleware: Starlette/FastAPI ``BaseHTTPMiddleware``.
"""

import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, DispatchFunction
from starlette.types import ASGIApp

from common.context import set_correlation_id, set_request_id, set_trace_id

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

logger = structlog.get_logger(__name__)


class DjangoRequestLoggingMiddleware:
    """Callable Django middleware for structured request/response logging.

    Emits the same ``request_started``, ``request_finished``, and
    ``request_exception`` events as :class:`FastAPIRequestLoggingMiddleware` so that
    Django admin and any other Django-handled paths produce identical log
    schema.

    Attributes:
        get_response: The next callable in the Django middleware chain.
        exempt_paths: Set of path prefixes that skip logging.
    """

    def __init__(self, get_response: "Callable[[HttpRequest], HttpResponse]") -> None:
        """Initialise with the next middleware or view callable.

        Args:
            get_response: Django callable that returns a response for a request.
        """
        self.get_response = get_response
        self.exempt_paths = {
            "/api/health",
            "/api/v1/ping",
            "/api/v1/health",
            "/admin/jsi18n/",
        }

    def __call__(self, request: "HttpRequest") -> "HttpResponse":
        """Process the request through the Django middleware chain.

        Args:
            request: Incoming Django HTTP request.

        Returns:
            The HTTP response with ``X-Request-ID``, ``X-Trace-ID``, and
            ``X-Correlation-ID`` headers set.
        """
        if any(request.path.startswith(p) for p in self.exempt_paths):
            return self.get_response(request)

        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())

        set_request_id(request_id)
        set_trace_id(trace_id)
        set_correlation_id(correlation_id)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            client_ip=request.META.get("REMOTE_ADDR", "unknown"),
        )

        logger.info(
            "request_started",
            request_path=request.get_full_path(),
            request_method=request.method,
            user_agent=request.headers.get("user-agent"),
        )

        start = time.perf_counter()
        try:
            response = self.get_response(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request_exception",
                ex_type=type(exc).__name__,
                ex_msg=str(exc),
                duration_ms=duration_ms,
                exc_info=True,
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_finished",
            request_path=request.get_full_path(),
            request_method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response["X-Request-ID"] = request_id
        response["X-Trace-ID"] = trace_id
        response["X-Correlation-ID"] = correlation_id
        structlog.contextvars.clear_contextvars()
        return response


class FastAPIRequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging of HTTP requests and responses.

    For every request this middleware:
    1. Reads ``X-Request-ID``, ``X-Trace-ID``, and ``X-Correlation-ID`` from
       incoming headers, generating UUID4 values for any that are absent.
    2. Stores all three IDs in :mod:`common.context` ContextVars for use by
       downstream code (Celery tasks, repositories, etc.).
    3. Clears and rebinds structlog context variables so every log line
       automatically carries these IDs.
    4. Logs a ``request_started`` event before dispatching.
    5. Logs a ``request_finished`` event after the response with
       ``status_code`` and ``duration_ms``.
    6. Sets ``X-Request-ID``, ``X-Trace-ID``, and ``X-Correlation-ID``
       response headers.

    Attributes:
        exempt_paths: Set of URL paths that bypass logging entirely
            (e.g. health probes, API docs).
    """

    def __init__(self, app: ASGIApp, dispatch: DispatchFunction | None = None):
        """Initialise the middleware and configure the exempt-path set.

        Args:
            app: ASGI application wrapped by this middleware.
            dispatch: Optional custom dispatch function; forwarded to
                :class:`~starlette.middleware.base.BaseHTTPMiddleware`.
        """
        super().__init__(app, dispatch)
        self.exempt_paths = {
            "/api/health",
            "/api/v1/ping",
            "/api/v1/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process a request with structured logging and timing.

        Args:
            request: The incoming FastAPI/Starlette request.
            call_next: Callable that forwards the request to the next
                middleware or route handler.

        Returns:
            The response with ``X-Request-ID``, ``X-Trace-ID``, and
            ``X-Correlation-ID`` headers added.
        """
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        client_ip = request.client.host if request.client else "unknown"

        set_request_id(request_id)
        set_trace_id(trace_id)
        set_correlation_id(correlation_id)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            client_ip=client_ip,
        )

        logger.info(
            "request_started",
            request_path=request.url.path,
            request_method=request.method,
            user_agent=request.headers.get("user-agent"),
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request_exception",
                ex_type=type(exc).__name__,
                ex_msg=str(exc),
                duration_ms=duration_ms,
                exc_info=True,
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_finished",
            request_path=request.url.path,
            request_method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response
