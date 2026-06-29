"""Per-user token-version gate for instant access-token invalidation.

An access token is a self-contained snapshot: ``is_superuser``, ``is_staff``,
``roles``, ``scopes`` and ``companies`` are baked in at mint time and verified
downstream with no DB lookup. That snapshot stays stale until the token
expires, so a server-side authorisation change (company removed, group
removed, staff flag cleared, group permissions edited) does not reach a
live token on its own.

:class:`TokenVersionService` closes that gap for tokens checked against
rudra. It keeps a monotonically increasing integer per user in the Django
cache (Redis at runtime):

* The current version is embedded as the ``ver`` claim when a token is
  minted (see ``get_user_token_claims``).
* On every request, the gate in :mod:`common.auth.dependencies` compares the
  token's ``ver`` against the current value; a token minted before the latest
  bump is rejected, forcing the client to refresh and pick up fresh claims.
* An authorisation change calls :meth:`bump` (or :meth:`bump_many`) to
  invalidate every access token the affected user is currently holding.

The cache is the single source of truth, mirroring the ``blacklist:<jti>``
mechanism in :mod:`common.auth.jwt.handler`: an absent key reads as version
``0`` (a freshly-seen user), and a cache flush re-admits outstanding tokens
only until their natural expiry — the same bounded exposure the blacklist
already accepts.

In services that do not own the rudra cache (the downstream peers that carry
a verbatim copy of ``common/``) the key is never written, so :meth:`get`
always returns ``0`` and the gate is inert — those services rely on the
access-token lifetime instead. Only rudra maintains the counter.

Use the module-level singleton :data:`token_version_service`; do not
construct the class directly.
"""

from __future__ import annotations

from asgiref.sync import sync_to_async
from django.core.cache import cache

_KEY_PREFIX = "user_token_version"


def _key(user_id: int | str) -> str:
    """Return the cache key holding *user_id*'s current token version."""
    return f"{_KEY_PREFIX}:{user_id}"


class TokenVersionService:
    """Read and increment per-user token versions in the Django cache.

    Stateless apart from the shared cache; safe to use as a process-wide
    singleton. Versions never expire (``timeout=None``) so a bump survives
    for as long as the cache backend retains the key.
    """

    def get(self, user_id: int | str) -> int:
        """Return the current token version for *user_id* (``0`` if unset).

        Args:
            user_id: PK of the user.

        Returns:
            The current integer version, or ``0`` when no bump has ever been
            recorded (or the key is not maintained in this service).
        """
        return int(cache.get(_key(user_id)) or 0)

    def bump(self, user_id: int | str) -> int:
        """Invalidate every live access token for *user_id*.

        Increments the user's version so any token carrying an older ``ver``
        claim is rejected at the gate. Seeds the counter at ``1`` when the key
        does not yet exist.

        Args:
            user_id: PK of the user whose tokens should be invalidated.

        Returns:
            The new version value.
        """
        key = _key(user_id)
        try:
            return int(cache.incr(key))
        except ValueError:
            cache.set(key, 1, timeout=None)
            return 1

    def bump_many(self, user_ids: list[int] | list[str]) -> None:
        """Invalidate live access tokens for several users (group fan-out).

        Args:
            user_ids: PKs whose tokens should be invalidated. Duplicates and
                an empty list are both handled safely.
        """
        for user_id in set(user_ids):
            self.bump(user_id)

    async def aget(self, user_id: int | str) -> int:
        """Async variant of :meth:`get`."""
        return await sync_to_async(self.get, thread_sensitive=True)(user_id)

    async def abump(self, user_id: int | str) -> int:
        """Async variant of :meth:`bump`."""
        return await sync_to_async(self.bump, thread_sensitive=True)(user_id)

    async def abump_many(self, user_ids: list[int] | list[str]) -> None:
        """Async variant of :meth:`bump_many`."""
        await sync_to_async(self.bump_many, thread_sensitive=True)(user_ids)


token_version_service = TokenVersionService()
