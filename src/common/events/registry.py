"""Global event dispatcher singleton.

Import ``event_dispatcher`` from this module (or from ``common.events``)
whenever you need to publish or subscribe to domain events.
"""

from common.events.base import EventDispatcher

event_dispatcher = EventDispatcher()
