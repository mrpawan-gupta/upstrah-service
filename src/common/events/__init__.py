"""Lightweight in-process event bus for domain events.

Provides :class:`DomainEvent`, :class:`EventHandler`, and
:class:`EventDispatcher` — the building blocks for decoupled,
event-driven workflows (e.g. OTP delivery via pluggable providers).
"""

from common.events.base import DomainEvent, EventDispatcher, EventHandler
from common.events.registry import event_dispatcher

__all__ = [
    "DomainEvent",
    "EventDispatcher",
    "EventHandler",
    "event_dispatcher",
]
