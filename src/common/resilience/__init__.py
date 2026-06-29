"""Resilience utilities for external service calls.

Provides a reusable ``CircuitBreaker`` that can wrap any callable to
protect against cascading failures when an external dependency is
unavailable.
"""

from common.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpenError",
]
