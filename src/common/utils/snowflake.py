"""Snowflake ID generation utilities.

Implements a variant of Twitter's Snowflake algorithm: a 64-bit, time-ordered,
distributed-safe unique identifier.

Bit layout (MSB → LSB)::

    Bits 63–22  timestamp  (41 bits — milliseconds relative to epoch)
    Bits 21–12  instance   (10 bits — worker / machine ID, 0–1023)
    Bits 11–0   sequence   (12 bits — per-millisecond counter, 0–4095)

Typical usage::

    gen = SnowflakeGenerator(instance=1, epoch=1_700_000_000_000)
    sf_id = next(gen)           # integer Snowflake ID, or None if exhausted
    sf    = Snowflake.parse(sf_id, epoch=1_700_000_000_000)
    print(sf.datetime)          # UTC datetime
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from time import sleep, time

__all__ = ("Snowflake", "SnowflakeGenerator", "generate_snowflake")

MAX_TS: int = (1 << 41) - 1
MAX_INSTANCE: int = (1 << 10) - 1
MAX_SEQ: int = (1 << 12) - 1
_TS_SHIFT: int = 22
_INST_SHIFT: int = 12


@dataclass(frozen=True)
class Snowflake:
    """Immutable value object representing a decoded Snowflake ID.
    Attributes:
        timestamp:  Epoch-relative milliseconds extracted from the ID (41 bits).
        instance:   Worker / machine identifier, 0–1023 (10 bits).
        epoch:      Custom epoch offset in Unix milliseconds (default ``0``
                    means the standard Unix epoch).
        seq:        Per-millisecond sequence counter, 0–4095 (12 bits).
    """

    timestamp: int
    instance: int
    epoch: int = 0
    seq: int = 0

    def __post_init__(self) -> None:
        """Validate that all field values are within their legal bit-width ranges.

        Raises:
            ValueError: If any field is outside its valid range.
        """
        if self.epoch < 0:
            raise ValueError(f"epoch must be >= 0, got {self.epoch}")
        if not (0 <= self.timestamp <= MAX_TS):
            raise ValueError(
                f"timestamp must be in [0, {MAX_TS}], got {self.timestamp}"
            )
        if not (0 <= self.instance <= MAX_INSTANCE):
            raise ValueError(
                f"instance must be in [0, {MAX_INSTANCE}], got {self.instance}"
            )
        if not (0 <= self.seq <= MAX_SEQ):
            raise ValueError(f"seq must be in [0, {MAX_SEQ}], got {self.seq}")

    @classmethod
    def parse(cls, snowflake: int, epoch: int = 0) -> "Snowflake":
        """Decode a raw 64-bit Snowflake integer into its component fields.
        Args:
            snowflake:  The raw integer ID to decode.
            epoch:      Custom epoch offset in Unix milliseconds used when
                        the ID was generated.
        Returns:
            A new :class:`Snowflake` instance with the decoded fields.
        """
        return cls(
            epoch=epoch,
            timestamp=snowflake >> _TS_SHIFT,
            instance=(snowflake >> _INST_SHIFT) & MAX_INSTANCE,
            seq=snowflake & MAX_SEQ,
        )

    @property
    def milliseconds(self) -> int:
        """Absolute Unix timestamp in milliseconds."""
        return self.timestamp + self.epoch

    @property
    def seconds(self) -> float:
        """Absolute Unix timestamp in seconds."""
        return self.milliseconds / 1000

    @property
    def datetime(self) -> datetime:
        """UTC :class:`~datetime.datetime` equivalent of this Snowflake."""
        return datetime.utcfromtimestamp(self.seconds)

    def datetime_tz(self, tz: tzinfo | None = None) -> datetime:
        """Timezone-aware :class:`~datetime.datetime` equivalent of this Snowflake.

        Args:
            tz: Target timezone.  Defaults to the local system timezone when
                ``None`` is passed to :func:`datetime.fromtimestamp`.
        """
        return datetime.fromtimestamp(self.seconds, tz=tz)

    @property
    def timedelta(self) -> timedelta:
        """The custom epoch offset expressed as a :class:`~datetime.timedelta`."""
        return timedelta(milliseconds=self.epoch)

    @property
    def value(self) -> int:
        """Re-encode the decoded fields back into a 64-bit Snowflake integer."""
        return (self.timestamp << _TS_SHIFT) | (self.instance << _INST_SHIFT) | self.seq


class SnowflakeGenerator:
    """Iterator that yields unique Snowflake IDs for a single worker instance.

    Each :func:`next` call returns either a new integer Snowflake ID or
    ``None`` when the 12-bit sequence counter is exhausted within the current
    millisecond, or when the system clock moves backwards.  Callers should
    retry on ``None`` (typically after a brief sleep or spin).

    The generator object is pre-shifted so that the hot :meth:`__next__` path
    performs only two bitwise-OR operations instead of shifts.

    Example::

        gen = SnowflakeGenerator(instance=0, epoch=1_700_000_000_000)
        while (sf_id := next(gen)) is None:
            pass   # spin until the next millisecond tick
        print(sf_id)

    Args:
        instance:   Worker / machine identifier, 0–1023.
        seq:        Initial sequence value (default ``0``).
        epoch:      Custom epoch offset in Unix milliseconds (default ``0``).
        timestamp:  Override the starting Unix timestamp in milliseconds
                    (default: current time).
    """

    __slots__ = ("_epo", "_inf", "_seq", "_ts")

    def __init__(
        self,
        instance: int,
        *,
        seq: int = 0,
        epoch: int = 0,
        timestamp: int | None = None,
    ) -> None:
        """Initialise the generator and validate all parameters.

        Args:
            instance: Worker / machine identifier, 0–1023.
            seq: Initial sequence value (default ``0``).
            epoch: Custom epoch offset in Unix milliseconds (default ``0``).
            timestamp: Override the starting Unix timestamp in milliseconds
                (default: current system time).

        Raises:
            OverflowError: If the current timestamp has exceeded the 41-bit
                maximum.
            ValueError: If any argument is outside its valid range.
        """
        current = int(time() * 1000)

        if current >= MAX_TS:
            raise OverflowError(
                "The maximum timestamp has been reached; "
                "Snowflake cannot generate more IDs."
            )
        if not (0 <= epoch <= current):
            raise ValueError(f"epoch must be in [0, {current}], got {epoch}")

        ts = timestamp if timestamp is not None else current
        if not (0 <= ts <= current):
            raise ValueError(f"timestamp must be in [0, {current}], got {ts}")

        if not (0 <= instance <= MAX_INSTANCE):
            raise ValueError(f"instance must be in [0, {MAX_INSTANCE}], got {instance}")
        if not (0 <= seq <= MAX_SEQ):
            raise ValueError(f"seq must be in [0, {MAX_SEQ}], got {seq}")

        self._epo: int = epoch
        self._ts: int = ts - epoch
        self._inf: int = instance << _INST_SHIFT
        self._seq: int = seq

    @classmethod
    def from_snowflake(cls, sf: Snowflake) -> "SnowflakeGenerator":
        """Resume generation immediately after an existing Snowflake ID.

        The new generator shares the same epoch and instance as ``sf`` and
        starts from ``sf``'s sequence counter.

        Args:
            sf: The Snowflake to resume from.

        Returns:
            A new :class:`SnowflakeGenerator` initialised with the same
            instance and epoch as ``sf``, starting from ``sf``'s sequence
            counter.
        """
        # Use sf.milliseconds (absolute Unix ms) so that __init__ can
        # correctly subtract the epoch without double-applying it.
        return cls(sf.instance, seq=sf.seq, epoch=sf.epoch, timestamp=sf.milliseconds)

    @property
    def epoch(self) -> int:
        """The custom epoch offset (Unix ms) used by this generator."""
        return self._epo

    def __iter__(self) -> "SnowflakeGenerator":
        """Return ``self`` to satisfy the iterator protocol."""
        return self

    def __next__(self) -> int | None:
        """Return the next unique Snowflake ID, or ``None`` on contention.
        Returns ``None`` in two situations:
        * The 12-bit sequence counter reached its maximum within the current
          millisecond (sequence exhaustion).
        * The system clock moved backwards relative to the last generated
          timestamp (clock skew).
        Callers should treat ``None`` as a signal to retry.
        """
        current = int(time() * 1000) - self._epo

        if current == self._ts:
            if self._seq == MAX_SEQ:
                return None  # Sequence exhausted; caller must retry next tick.
            self._seq += 1
        elif current < self._ts:
            return None  # Clock moved backwards; refuse to produce duplicate IDs.
        else:
            self._seq = 0
        self._ts = current
        return (self._ts << _TS_SHIFT) | self._inf | self._seq


_DEFAULT_MAX_RETRIES = 8
_RETRY_SLEEP_SECONDS = 0.001  # 1 ms back-off between retries


def generate_snowflake(
    *,
    instance: int | None = None,
    epoch: int | None = None,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> int:
    """Return a new Snowflake ID as an ``int`` — suitable as a model PK.

    This is a thin convenience wrapper over :class:`SnowflakeGenerator`
    that reads ``SNOWFLAKE_INSTANCE`` and ``SNOWFLAKE_EPOCH`` from Django
    settings when the corresponding argument is not supplied.

    The :class:`SnowflakeGenerator` iterator returns ``None`` on
    sequence-exhaustion or clock skew, so this helper retries a small
    number of times (with a 1 ms sleep between attempts) before giving
    up. In practice the retry path is almost never hit at typical
    insertion rates.

    Args:
        instance: Worker / machine identifier (0–1023). Defaults to
            ``settings.SNOWFLAKE_INSTANCE`` when omitted.
        epoch: Custom epoch offset in Unix milliseconds. Defaults to
            ``settings.SNOWFLAKE_EPOCH`` when omitted.
        max_retries: Maximum retry attempts on contention. Defaults to
            ``8``.

    Returns:
        A new 64-bit Snowflake ID as an integer.

    Raises:
        RuntimeError: If the generator repeatedly returned ``None`` for
            ``max_retries`` attempts (would indicate sustained clock
            skew or catastrophic sequence exhaustion).
    """
    if instance is None or epoch is None:
        # Deferred import — this module must be safe to import outside
        # a configured Django context (e.g. pure-Python unit tests).
        from django.conf import settings

        if instance is None:
            instance = int(getattr(settings, "SNOWFLAKE_INSTANCE", 0))
        if epoch is None:
            epoch = int(getattr(settings, "SNOWFLAKE_EPOCH", 1609459200000))

    generator = SnowflakeGenerator(instance=instance, epoch=epoch)
    for _ in range(max_retries):
        value = next(generator)
        if value is not None:
            return value
        sleep(_RETRY_SLEEP_SECONDS)
    raise RuntimeError(
        "Snowflake generation failed after "
        f"{max_retries} retries (clock skew or sequence exhaustion)."
    )
