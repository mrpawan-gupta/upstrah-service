"""Base class for all Celery task dispatchers.

Every service that enqueues Celery tasks as a business side-effect must
extend :class:`BaseCeleryDispatcher` rather than calling ``apply_async``
directly.  The base centralises three cross-cutting concerns:

1. **``transaction.on_commit`` wrapping** — tasks are enqueued only after
   the surrounding DB transaction commits.  Without this, the worker can
   read a row that has not yet been written.  ``on_commit=True`` is the
   default; set ``on_commit=False`` only for tasks that do not read the
   row that triggered the dispatch, and document the reason.

2. **Correlation / trace ID propagation** — ``correlation_id_var``,
   ``trace_id_var``, and ``request_id_var`` from the inbound request
   context are injected as Celery task headers so worker logs join the
   originating request in any log aggregation system.

3. **Consistent structlog event** — every dispatch emits a single
   ``celery_task_enqueued`` log line with ``task_name``, ``queue``, and
   ``kwargs_keys`` so dispatch is always observable without manual
   instrumentation in subclasses.

Usage
-----
Define an interface in ``<app>/api/application/interfaces/``::

    class IXDispatcher(abc.ABC):
        @abc.abstractmethod
        async def enqueue_operation(self, *, id_: int) -> None: ...

Implement the adapter in ``<app>/api/infrastructure/services/``::

    class CeleryXDispatcher(BaseCeleryDispatcher, IXDispatcher):
        QUEUE = "my_queue"

        async def enqueue_operation(self, *, id_: int) -> None:
            await self._enqueue(
                publish_x_task, kwargs={"id": id_}, queue=self.QUEUE
            )

Inject the interface into the use case via the DI container; the use case
never imports ``CeleryXDispatcher`` directly.
"""

from __future__ import annotations

from typing import Any

import structlog
from asgiref.sync import sync_to_async
from celery import Task
from django.db import transaction

from common.context import correlation_id_var, request_id_var, trace_id_var

logger = structlog.get_logger(__name__)


class BaseCeleryDispatcher:
    """Mixin base for Celery dispatch adapters.

    Subclasses combine this with a domain-specific ``IXDispatcher`` ABC::

        class CeleryXDispatcher(BaseCeleryDispatcher, IXDispatcher): ...

    The protected helpers ``_enqueue`` and ``_enqueue_bulk`` are the only
    permitted way to call ``apply_async`` in this codebase.
    """

    async def _enqueue(
        self,
        task: Task,
        *,
        kwargs: dict[str, Any],
        queue: str,
        on_commit: bool = True,
        countdown: int | None = None,
    ) -> None:
        """Enqueue a single Celery task, optionally deferring to DB commit.

        Args:
            task: The Celery task object (e.g. ``publish_x_task``).
            kwargs: Task keyword arguments.  Always passed as ``kwargs=``
                so the task signature stays explicit and order-independent.
            queue: Celery queue name.
            on_commit: When ``True`` (default), the enqueue is wrapped in
                ``transaction.on_commit`` so the task fires only after the
                surrounding transaction is committed.  Set to ``False`` only
                for tasks that do not read the triggering row.
            countdown: Optional delay in seconds before the task executes.
        """
        headers = self._build_headers()

        def _send() -> None:
            task.apply_async(
                kwargs=kwargs,
                queue=queue,
                headers=headers,
                countdown=countdown,
            )
            logger.info(
                "celery_task_enqueued",
                task_name=task.name,
                queue=queue,
                kwargs_keys=list(kwargs.keys()),
                on_commit=on_commit,
            )

        if on_commit:
            # transaction.on_commit is a no-op outside an atomic block, so it
            # is safe to wrap unconditionally — outside a transaction the
            # callback fires immediately after the call returns.
            await sync_to_async(transaction.on_commit)(_send)
        else:
            await sync_to_async(_send)()

    async def _enqueue_bulk(
        self,
        task: Task,
        *,
        kwargs_list: list[dict[str, Any]],
        queue: str,
        on_commit: bool = True,
    ) -> None:
        """Enqueue one task per entry in ``kwargs_list``.

        One ``apply_async`` call per row keeps per-row retry visibility and
        avoids a single large batch task becoming an atomicity footgun.  If
        true batch dispatch is ever needed (e.g. ``celery.group``), swap the
        implementation here without touching callers.

        Args:
            task: The Celery task object.
            kwargs_list: List of kwargs dicts, one per task invocation.
            queue: Celery queue name.
            on_commit: Same semantics as :meth:`_enqueue`.
        """
        for kwargs in kwargs_list:
            await self._enqueue(task, kwargs=kwargs, queue=queue, on_commit=on_commit)

    @classmethod
    def enqueue_on_commit(cls, task: Task, *, kwargs: dict[str, Any]) -> None:
        """Sync-safe enqueue for model hooks and signal handlers.

        Wraps ``apply_async`` in ``transaction.on_commit`` so the worker
        never reads an uncommitted row.  Propagates correlation/trace/request
        IDs from the current context into Celery task headers.

        Use this from ``@hook`` methods (which are synchronous).
        Use ``_enqueue()`` from async use-case code.

        Args:
            task: The Celery task object.
            kwargs: Task keyword arguments.
        """
        headers = cls._build_headers()
        transaction.on_commit(lambda: task.apply_async(kwargs=kwargs, headers=headers))
        logger.info(
            "celery_task_enqueued_on_commit",
            task_name=task.name,
            kwargs_keys=list(kwargs.keys()),
        )

    @staticmethod
    def _build_headers() -> dict[str, str]:
        """Extract request-context IDs and return them as Celery task headers.

        The worker reads these headers in the ``before_task_publish`` /
        ``task_prerun`` Celery signals registered by
        ``common.observability.celery_signals`` and re-binds them to the
        worker's structlog context so worker logs are correlated with the
        originating HTTP request.
        """
        headers: dict[str, str] = {}
        if cid := correlation_id_var.get(""):
            headers["correlation_id"] = cid
        if tid := trace_id_var.get(""):
            headers["trace_id"] = tid
        if rid := request_id_var.get(""):
            headers["request_id"] = rid
        return headers
