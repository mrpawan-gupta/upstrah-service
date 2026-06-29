"""Time utility helpers for the VMS application.

Provides timezone-aware datetime helpers used throughout the codebase
to avoid accidental use of naive datetimes.
"""

from datetime import UTC, datetime


def now_utc() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    Returns:
        Current :class:`~datetime.datetime` with ``tzinfo=UTC``.
    """
    return datetime.now(UTC)
