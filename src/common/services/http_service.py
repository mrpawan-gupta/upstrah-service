"""Central HTTP client with circuit breaker protection.

Provides :class:`HttpClient`, a thin wrapper around ``httpx.Client`` that
routes every request through a :class:`~common.resilience.CircuitBreaker`.
All outbound HTTP calls in kriya-service should go through an ``HttpClient``
instance so that circuit breaker state is tracked per logical service.

Network and timeout errors (``httpx.RequestError``) count as circuit breaker
failures.  HTTP-level status codes do **not** — callers inspect the returned
``httpx.Response`` themselves.

Usage::

    from common.services import HttpClient
    from common.resilience import CircuitBreakerOpenError

    # Lazy singleton — created once, reused across callers
    kriya = HttpClient.get_instance("kriya", base_url="http://localhost:8002", timeout=2.0)

    try:
        resp = kriya.post("/config/api/v1/events", json=payload, headers=headers)
    except CircuitBreakerOpenError:
        ...  # service is down, fast-fail

Configuration knobs (per-instance):

* ``failure_threshold`` — consecutive failures before the circuit opens.
* ``recovery_timeout`` — seconds in open state before allowing a probe.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import httpx
import structlog

from common.resilience import CircuitBreaker, CircuitBreakerOpenError

logger = structlog.get_logger(__name__)


class HttpClient:
    """HTTP client with per-service circuit breaker protection.

    Use :meth:`get_instance` to obtain a **lazy singleton** keyed by
    ``name``.  The first call creates the instance; subsequent calls with
    the same ``name`` return the cached one so circuit breaker state
    persists across callers.

    Each instance manages a named :class:`~common.resilience.CircuitBreaker`
    that tracks consecutive transport-level failures for one logical service.
    All HTTP methods (``get``, ``post``, ``put``, ``patch``, ``delete``)
    route through :meth:`request`, which executes the call inside the
    circuit breaker.

    A fresh ``httpx.Client`` is created per request (matching the existing
    fire-and-forget pattern).  To override the timeout on a single call,
    pass ``timeout=`` to any method.

    Raises :class:`~common.resilience.CircuitBreakerOpenError` when the
    circuit is open.  Callers decide how to handle it (log + suppress for
    fire-and-forget, or propagate for request-path calls).

    Attributes:
        name: Human-readable service name (used for CB naming and logging).
        base_url: Prefix prepended to relative paths.
        timeout: Default request timeout in seconds.
    """

    _instances: dict[str, HttpClient] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        name: str,
        base_url: str = "",
        timeout: float = 5.0,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        """Initialise the client and its circuit breaker.

        Prefer :meth:`get_instance` over direct construction so the
        circuit breaker state is shared across all callers for a given
        service ``name``.

        Args:
            name: Identifier for logging and circuit breaker naming.
            base_url: Prepended to relative paths (e.g. ``http://localhost:8002``).
            timeout: Default request timeout in seconds.
            failure_threshold: Consecutive transport failures before the circuit opens.
            recovery_timeout: Seconds in open state before allowing a probe request.
        """
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._cb = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exceptions=(httpx.RequestError,),
        )

    @classmethod
    def get_instance(
        cls,
        name: str,
        base_url: str = "",
        timeout: float = 5.0,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> HttpClient:
        """Return (or create) a singleton ``HttpClient`` keyed by *name*.

        Thread-safe.  The first call with a given *name* creates the
        instance using the supplied parameters; subsequent calls return the
        cached instance (extra parameters are ignored).

        Args:
            name: Unique service identifier (e.g. ``"kriya"``).
            base_url: Prepended to relative paths.
            timeout: Default request timeout in seconds.
            failure_threshold: Consecutive failures before the circuit opens.
            recovery_timeout: Seconds in open state before probing.

        Returns:
            The singleton :class:`HttpClient` for *name*.
        """
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    cls._instances[name] = cls(
                        name=name,
                        base_url=base_url,
                        timeout=timeout,
                        failure_threshold=failure_threshold,
                        recovery_timeout=recovery_timeout,
                    )
        return cls._instances[name]

    @property
    def circuit_state(self) -> str:
        """Return the current circuit breaker state.

        Returns:
            One of ``"closed"``, ``"open"``, or ``"half_open"``.
        """
        return self._cb.state

    def _build_url(self, path: str) -> str:
        """Resolve *path* against :attr:`base_url`.

        Absolute URLs (``http://`` / ``https://``) are returned as-is.
        Relative paths are prefixed with :attr:`base_url`.

        Args:
            path: Absolute URL or path relative to :attr:`base_url`.

        Returns:
            Fully-qualified URL string.
        """
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request through the circuit breaker.

        Args:
            method: HTTP method (``GET``, ``POST``, etc.).
            path: Absolute URL or path appended to :attr:`base_url`.
            json: JSON-serialisable body (mutually exclusive with *data*).
            data: Form-encoded body dict.
            headers: Extra request headers.
            params: URL query parameters.
            timeout: Per-request timeout override (seconds).

        Returns:
            The ``httpx.Response`` object.

        Raises:
            CircuitBreakerOpenError: If the circuit is open.
            httpx.RequestError: On transport-level failures (also counted
                as a circuit breaker failure).
        """
        url = self._build_url(path)
        effective_timeout = timeout if timeout is not None else self.timeout

        def _do() -> httpx.Response:
            with httpx.Client(timeout=effective_timeout) as client:
                return client.request(
                    method,
                    url,
                    json=json,
                    data=data,
                    headers=headers,
                    params=params,
                )

        logger.info(
            "http_request_out",
            service=self.name,
            method=method,
            url=url,
            circuit_state=self._cb.state,
        )

        start = time.monotonic()
        try:
            resp = self._cb.call(_do)
        except CircuitBreakerOpenError:
            logger.info(
                "http_request_rejected",
                service=self.name,
                method=method,
                url=url,
                reason="circuit_open",
            )
            raise
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info(
                "http_request_error",
                service=self.name,
                method=method,
                url=url,
                elapsed_ms=round(elapsed_ms, 1),
                ex_msg=str(exc),
                ex_type=type(exc).__name__,
                exc_info=True,
            )
            raise

        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "http_request_in",
            service=self.name,
            method=method,
            url=url,
            status=resp.status_code,
            elapsed_ms=round(elapsed_ms, 1),
        )
        return resp

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """Shorthand for ``request("POST", path, ...)``.

        Args:
            path: Absolute URL or path appended to :attr:`base_url`.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            The ``httpx.Response`` object.
        """
        return self.request("POST", path, **kwargs)

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """Shorthand for ``request("GET", path, ...)``.

        Args:
            path: Absolute URL or path appended to :attr:`base_url`.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            The ``httpx.Response`` object.
        """
        return self.request("GET", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        """Shorthand for ``request("PUT", path, ...)``.

        Args:
            path: Absolute URL or path appended to :attr:`base_url`.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            The ``httpx.Response`` object.
        """
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        """Shorthand for ``request("PATCH", path, ...)``.

        Args:
            path: Absolute URL or path appended to :attr:`base_url`.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            The ``httpx.Response`` object.
        """
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        """Shorthand for ``request("DELETE", path, ...)``.

        Args:
            path: Absolute URL or path appended to :attr:`base_url`.
            **kwargs: Forwarded to :meth:`request`.

        Returns:
            The ``httpx.Response`` object.
        """
        return self.request("DELETE", path, **kwargs)
