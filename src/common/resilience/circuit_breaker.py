"""Thread-safe circuit breaker for external service calls.

Implements the standard three-state pattern (CLOSED → OPEN → HALF_OPEN)
to prevent cascading failures when an external dependency is unavailable.

Usage::

    cb = CircuitBreaker(
        name="payment_gateway",
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exceptions=(httpx.TimeoutException, httpx.RequestError),
    )

    try:
        result = cb.call(lambda: httpx.post(url, json=data))
    except CircuitBreakerOpenError:
        # Fast-fail: circuit is open, skip the call
        ...

Classes:
    CircuitBreakerOpenError: Raised when the circuit is open and calls are
        rejected without attempting the underlying function.
    CircuitBreaker: The circuit breaker implementation.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

import structlog
from starlette import status

from common.exceptions.exceptions import AppBaseError

logger = structlog.get_logger(__name__)

T = TypeVar("T")

_STATE_CLOSED = "closed"
_STATE_OPEN = "open"
_STATE_HALF_OPEN = "half_open"


class CircuitBreakerOpenError(AppBaseError):
    """Raised when the circuit breaker is open and rejecting calls.

    Inherits from ``AppBaseError`` so the universal exception handler
    converts it to an HTTP 503 Service Unavailable response.
    """

    def __init__(self, name: str) -> None:
        """Initialise with the circuit breaker's name for diagnostics.

        Args:
            name: The circuit breaker instance name.
        """
        super().__init__(
            message=f"Circuit breaker '{name}' is open — service temporarily unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.breaker_name = name


class CircuitBreaker:
    """Thread-safe circuit breaker for external service calls.

    States:

    - **CLOSED** (normal): calls pass through.  Failures increment a
      counter; when it reaches ``failure_threshold`` the circuit opens.
    - **OPEN** (failing): calls are rejected immediately with
      ``CircuitBreakerOpenError``.  After ``recovery_timeout`` seconds
      the circuit transitions to HALF_OPEN.
    - **HALF_OPEN** (probing): a single call is allowed through.  If it
      succeeds the circuit closes; if it fails the circuit reopens.

    Attributes:
        name: Human-readable identifier for logging and monitoring.
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout: Seconds to wait in OPEN state before probing.
        expected_exceptions: Exception types that count as failures.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        """Initialise a new circuit breaker.

        Args:
            name: Identifier used in log messages.
            failure_threshold: Consecutive failures that trigger the open state.
            recovery_timeout: Seconds in open state before allowing a probe.
            expected_exceptions: Exception types that count as failures.
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self._lock = threading.Lock()
        self._state = _STATE_CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._probing: bool = False

    @property
    def state(self) -> str:
        """Return the current circuit state as a string.

        Returns:
            One of ``"closed"``, ``"open"``, or ``"half_open"``.
        """
        with self._lock:
            if self._state == _STATE_OPEN and (
                self._probing or self._recovery_timeout_elapsed()
            ):
                return _STATE_HALF_OPEN
            return self._state

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute *func* through the circuit breaker.

        Args:
            func: The callable to execute.
            *args: Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func*.

        Raises:
            CircuitBreakerOpenError: If the circuit is open and the
                recovery timeout has not yet elapsed.
        """
        with self._lock:
            current_state = self._effective_state()

            if current_state == _STATE_OPEN:
                logger.info(
                    "circuit_breaker_rejected",
                    name=self.name,
                    failure_count=self._failure_count,
                )
                raise CircuitBreakerOpenError(self.name)

            # HALF_OPEN or CLOSED — allow the call
            if current_state == _STATE_HALF_OPEN:
                logger.info("circuit_breaker_probe", name=self.name)

        # Execute outside the lock to avoid holding it during I/O
        try:
            result = func(*args, **kwargs)
        except self.expected_exceptions as exc:
            self._record_failure()
            raise exc
        else:
            self._record_success()
            return result

    def _effective_state(self) -> str:
        """Return the effective state, allowing exactly one HALF_OPEN probe when timeout elapsed.

        Sets ``_probing = True`` and returns ``_STATE_HALF_OPEN`` for the first
        caller after the recovery timeout.  Subsequent callers continue to see
        ``_STATE_OPEN`` until the probe completes (success or failure).

        Must be called while holding ``self._lock``.
        """
        if (
            self._state == _STATE_OPEN
            and self._recovery_timeout_elapsed()
            and not self._probing
        ):
            self._probing = True
            return _STATE_HALF_OPEN
        return self._state

    def _recovery_timeout_elapsed(self) -> bool:
        """Check whether enough time has passed since the last failure.

        Must be called while holding ``self._lock``.
        """
        return (time.monotonic() - self._last_failure_time) >= self.recovery_timeout

    def _record_failure(self) -> None:
        """Increment the failure counter and open the circuit if threshold reached.

        When a HALF_OPEN probe fails (``_probing`` was set), the circuit
        remains open and the recovery timer resets.  The probe-failed branch
        is checked first so the correct log event is emitted regardless of
        the accumulated failure count.
        """
        with self._lock:
            was_probing = self._probing
            self._probing = False
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if was_probing:
                # Probe failed — circuit stays open, recovery timer resets
                logger.info(
                    "circuit_breaker_probe_failed",
                    name=self.name,
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = _STATE_OPEN
                logger.info(
                    "circuit_breaker_opened",
                    name=self.name,
                    failure_count=self._failure_count,
                )

    def _record_success(self) -> None:
        """Reset the failure counter and close the circuit."""
        with self._lock:
            was_probing = self._probing
            self._probing = False
            prev_state = self._state
            self._failure_count = 0
            self._state = _STATE_CLOSED
            if prev_state != _STATE_CLOSED or was_probing:
                logger.info(
                    "circuit_breaker_closed",
                    name=self.name,
                    previous_state=_STATE_HALF_OPEN if was_probing else prev_state,
                )
