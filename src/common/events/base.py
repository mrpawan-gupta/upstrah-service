"""Domain event primitives — event base class, handler protocol, and dispatcher.

The dispatcher supports both synchronous (in-process) and asynchronous
(Celery-deferred) event publishing so that handlers can run inline during
the request or be offloaded to a background worker.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    Attributes:
        occurred_at: UTC timestamp of when the event was created.
        metadata: Arbitrary key-value pairs for tracing / correlation.
    """

    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """Return the fully-qualified class name as the event type identifier."""
        return f"{type(self).__module__}.{type(self).__qualname__}"


class EventHandler(ABC):
    """Abstract handler that reacts to a specific domain event."""

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Process *event*.

        Args:
            event: The domain event to handle.
        """


class EventDispatcher:
    """In-process pub/sub dispatcher for domain events.

    Handlers are registered per event type.  When an event is published,
    all matching handlers are invoked sequentially.  Failures in one
    handler do not prevent subsequent handlers from running.
    """

    def __init__(self) -> None:
        """Initialise with an empty handler registry."""
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: EventHandler,
    ) -> None:
        """Register *handler* to be called when *event_type* is published.

        Args:
            event_type: The concrete ``DomainEvent`` subclass to listen for.
            handler: The handler instance to invoke.
        """
        self._handlers.setdefault(event_type, []).append(handler)
        logger.info(
            "event_handler_subscribed",
            event_type=event_type.__name__,
            handler=type(handler).__name__,
        )

    def unsubscribe(
        self,
        event_type: type[DomainEvent],
        handler: EventHandler,
    ) -> None:
        """Remove *handler* from the subscription list for *event_type*.

        Args:
            event_type: The event class to unsubscribe from.
            handler: The handler instance to remove.
        """
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish *event* to all registered handlers (in-process, sequential).

        Each handler is awaited in order.  If a handler raises, the error is
        logged and the remaining handlers still execute.

        Args:
            event: The domain event to dispatch.
        """
        event_name = type(event).__name__
        handlers = self._handlers.get(type(event), [])

        if not handlers:
            logger.info("event_no_handlers", event_name=event_name)
            return

        logger.info(
            "event_dispatching",
            event_name=event_name,
            handler_count=len(handlers),
        )

        for handler in handlers:
            handler_name = type(handler).__name__
            try:
                await handler.handle(event)
                logger.info(
                    "event_handler_success",
                    event_name=event_name,
                    handler=handler_name,
                )
            except Exception as exc:
                logger.info(
                    "event_handler_failed",
                    event_name=event_name,
                    handler=handler_name,
                    ex_msg=str(exc),
                    ex_type=type(exc).__name__,
                    exc_info=True,
                )

    def publish_sync(self, event: DomainEvent) -> None:
        """Publish *event* from a synchronous context.

        Creates or reuses an event loop to run :meth:`publish`.  Useful
        inside Celery tasks or other sync code paths.

        Args:
            event: The domain event to dispatch.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(self.publish(event))
        else:
            asyncio.run(self.publish(event))

    def has_handlers(self, event_type: type[DomainEvent]) -> bool:
        """Return ``True`` if at least one handler is registered for *event_type*.

        Args:
            event_type: The event class to check.
        """
        return bool(self._handlers.get(event_type))
