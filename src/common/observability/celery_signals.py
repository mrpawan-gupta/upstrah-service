"""Shared Celery signal handlers for every Rama-ecosystem service.

Binds structlog context variables so that every log line emitted during
task execution carries trace and task metadata. Trace IDs are propagated
from the originating HTTP request through ``before_task_publish``,
ensuring end-to-end traceability across async boundaries.

Usage — in each service's ``<project>/celery.py``::

    from common.observability.celery_signals import register_celery_signals
    register_celery_signals()

Calling :func:`register_celery_signals` connects the handlers to
Celery's signal bus. It is idempotent (guarded by a module-level flag)
so re-imports and test harness re-registration are safe.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from celery.signals import (
    before_task_publish,
    setup_logging,
    task_failure,
    task_postrun,
    task_prerun,
)

from common.context import get_trace_id

logger = structlog.get_logger(__name__)

_REGISTERED = False


def _get_received_time(metadata: dict[str, Any], task_attempt: int) -> float | None:
    """Return the broker-received timestamp for a given task attempt.

    Args:
        metadata: Metadata dict stored in the task headers by
            ``task_before_publish_handler``.
        task_attempt: Zero-based retry index from ``task.request.retries``.

    Returns:
        The float epoch timestamp when the attempt was received, or
        ``None`` if not available.
    """
    received_times = metadata.get("received_times", [])
    if len(received_times) > task_attempt:
        return received_times[task_attempt]
    return None


def _config_loggers(*args: Any, **kwargs: Any) -> None:
    """Configure logging for Celery by loading Django's ``LOGGING`` dict.

    Connected to Celery's ``setup_logging`` signal to prevent Celery
    from hijacking the service's structlog configuration.
    """
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


def _task_before_publish_handler(
    sender: str | None = None,
    body: Any = None,
    headers: dict[str, Any] | None = None,
    **kwargs: Any,
) -> None:
    """Inject the current trace ID into task headers before publishing.

    Captures the trace ID from the active request context and stores it
    in ``headers["__metadata__"]`` so the worker can restore it during
    ``task_prerun_handler``.
    """
    try:
        if headers is None:
            return
        trace_id = get_trace_id()
        metadata = headers.get("__metadata__", {})
        metadata["trace_id"] = trace_id
        headers["__metadata__"] = metadata
    except Exception as exc:
        logger.info(
            "task_before_publish_failed",
            ex_msg=str(exc),
            ex_type=type(exc).__name__,
            exc_info=True,
        )


def _task_prerun_handler(
    task_id: str | None = None, task: Any | None = None, **kwargs: Any
) -> None:
    """Clear structlog context, bind task metadata, and log task start.

    Restores the trace ID propagated via ``before_task_publish``, falling
    back to a fresh UUID when none is present. Records task start time
    in metadata for execution-time calculation in ``task_postrun_handler``.
    """
    try:
        metadata = getattr(task.request, "__metadata__", {})
        task_name = getattr(task, "name", None)
        queue_name = getattr(task.request, "delivery_info", {}).get(
            "routing_key", "celery"
        )
        trace_id = metadata.get("trace_id") or str(uuid.uuid4())
        metadata["start_time"] = time.time()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            celery_task_id=task_id,
            celery_task_name=task_name,
            queue_name=queue_name,
            trace_id=trace_id,
        )
        logger.info("task_started", task_ref_id=task_id, queue_name=queue_name)
    except Exception as exc:
        logger.info(
            "task_prerun_failed",
            ex_msg=str(exc),
            ex_type=type(exc).__name__,
            exc_info=True,
        )


def _task_postrun_handler(
    task_id: str | None = None,
    task: Any | None = None,
    state: str | None = None,
    **kwargs: Any,
) -> None:
    """Log task completion with timing metrics and clear structlog context."""
    try:
        metadata = getattr(task.request, "__metadata__", {})
        task_name = getattr(task, "name", None)
        queue_name = getattr(task.request, "delivery_info", {}).get(
            "routing_key", "celery"
        )
        start_time = metadata.get("start_time")
        execution_time = round(time.time() - start_time, 3) if start_time else 0
        received_time = _get_received_time(metadata, task.request.retries)
        execution_delay = (
            round(start_time - received_time, 3)
            if (start_time and received_time)
            else 0
        )
        logger.info(
            "task_completed",
            state=state,
            task_id=task_id,
            task_name=task_name,
            queue_name=queue_name,
            execution_time=execution_time,
            execution_delay=execution_delay,
        )
        structlog.contextvars.clear_contextvars()
    except Exception as exc:
        logger.info(
            "task_postrun_failed",
            ex_msg=str(exc),
            ex_type=type(exc).__name__,
            exc_info=True,
        )


def _task_failure_handler(
    task_id: str | None = None,
    exception: BaseException | None = None,
    traceback: Any | None = None,
    **kwargs: Any,
) -> None:
    """Log task failure with exception details and a stack trace."""
    logger.info(
        "task_failed",
        ex_msg=str(exception),
        ex_type=type(exception).__name__ if exception else None,
        exc_info=True,
    )


def register_celery_signals() -> None:
    """Connect the shared handlers to Celery's signal bus.

    Idempotent — subsequent calls are no-ops. Each service's
    ``<project>/celery.py`` should call this once right after the
    ``celery_app`` singleton is constructed.
    """
    global _REGISTERED
    if _REGISTERED:
        return
    setup_logging.connect(_config_loggers, weak=False)
    before_task_publish.connect(_task_before_publish_handler, weak=False)
    task_prerun.connect(_task_prerun_handler, weak=False)
    task_postrun.connect(_task_postrun_handler, weak=False)
    task_failure.connect(_task_failure_handler, weak=False)
    _REGISTERED = True


__all__ = ["register_celery_signals"]
