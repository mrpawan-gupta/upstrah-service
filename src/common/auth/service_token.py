"""Client-side helper that fetches and caches service JWTs from rudra.

A Tolaram microservice (care, vms, kriya, or rudra itself for internal
fan-out) needs a bearer token when calling another service with no
logged-in user in context — startup lookups, Celery background tasks,
webhook dispatchers, etc. :class:`ServiceTokenManager` handles that
end-to-end:

1. On first :meth:`get_token` call, POST to the configured rudra
   ``/oauth/token`` endpoint with the ``client_credentials`` grant.
2. Cache the returned JWT in memory (process-local; restart-scoped).
3. Serve subsequent calls from cache until ``exp - now < refresh_skew``,
   then transparently re-fetch. A :class:`threading.Lock` ensures only
   one concurrent refresh per process.
4. If the refresh fails while a cached token is still valid, return
   the cached token so a transient rudra blip doesn't break fan-out.
   If the cache is empty, the exception propagates so the caller can
   fail fast.

The primary API is **synchronous** because the outbound dispatcher
(``common/services/dispatch.py``) runs on a sync httpx pipeline; the async
convenience :meth:`aget_token` simply offloads the sync call to a
thread so asyncio callers don't have to.

Singleton access: call :func:`get_service_token_manager` from
``common/services/dispatch.py`` and Celery task entry points; do not instantiate
the class directly.

Configuration (all from Django settings):

* ``SERVICE_CLIENT_ID`` — this service's ``ServiceClient.client_id``.
* ``SERVICE_CLIENT_SECRET`` — the raw secret paired with that client_id.
* ``RUDRA_BASE_URL`` — base URL of the rudra ``/oauth/token`` endpoint.
* ``SERVICE_TOKEN_REFRESH_SKEW_SECONDS`` — default 60; refresh this many
  seconds before ``exp`` to avoid mid-request expiry.
* ``SERVICE_TOKEN_REQUEST_TIMEOUT`` — default 5.0 seconds.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

import httpx
import jwt
import structlog
from django.conf import settings

logger = structlog.get_logger(__name__)

_TOKEN_URL_PATH = "/accounts/api/v1/oauth/token"


class ServiceTokenUnavailableError(RuntimeError):
    """Raised when a service token cannot be obtained AND no cache is warm.

    Callers that can gracefully degrade (e.g., fire-and-forget dispatch
    tasks) should catch this; callers on the request path should let
    it propagate.
    """


class ServiceTokenManager:
    """Fetches and caches service JWTs from rudra's ``/oauth/token``.

    Typical lifetime: one instance per process. The class is safe to use
    concurrently — token refresh is guarded by a :class:`threading.Lock`
    so only a single outbound request is in flight even when many
    request handlers simultaneously need a fresh token.

    Attributes:
        client_id: Configured ``SERVICE_CLIENT_ID``.
        base_url: Rudra base URL used for token requests.
        refresh_skew: Seconds before ``exp`` to refresh proactively.
        request_timeout: Per-request HTTP timeout in seconds.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
        refresh_skew: int | None = None,
        request_timeout: float | None = None,
    ) -> None:
        """Initialise from explicit arguments or Django settings.

        Every parameter has a settings fallback so production code can
        simply call ``ServiceTokenManager()``; tests may inject overrides.
        """
        self.client_id: str = client_id or getattr(settings, "SERVICE_CLIENT_ID", "")
        self._client_secret: str = client_secret or getattr(
            settings, "SERVICE_CLIENT_SECRET", ""
        )
        self.base_url: str = (
            base_url or getattr(settings, "RUDRA_BASE_URL", "")
        ).rstrip("/")
        self.refresh_skew: int = (
            refresh_skew
            if refresh_skew is not None
            else getattr(settings, "SERVICE_TOKEN_REFRESH_SKEW_SECONDS", 60)
        )
        self.request_timeout: float = (
            request_timeout
            if request_timeout is not None
            else getattr(settings, "SERVICE_TOKEN_REQUEST_TIMEOUT", 5.0)
        )

        self._token: str = ""
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    def _is_fresh(self) -> bool:
        """``True`` when the cached token is present and not near expiry."""
        if not self._token:
            return False
        return time.time() < (self._expires_at - self.refresh_skew)

    def get_token(self) -> str:
        """Return a valid service JWT, refreshing from rudra when stale.

        Returns:
            A freshly-signed or cached service bearer token.

        Raises:
            ServiceTokenUnavailableError: Rudra is unreachable AND no
                cached token is available.
            RuntimeError: Required settings are missing at call time.
        """
        if self._is_fresh():
            return self._token

        with self._lock:
            # Another concurrent call may have refreshed while we waited.
            if self._is_fresh():
                return self._token

            try:
                self._refresh()
            except Exception as exc:
                if self._token:
                    # Fall back to a still-valid cached token rather than
                    # bouncing a request that could otherwise succeed.
                    logger.info(
                        "service_token_refresh_failed_cached_hit",
                        client_id=self.client_id,
                        ex_msg=str(exc),
                        ex_type=type(exc).__name__,
                        exc_info=True,
                    )
                    return self._token
                logger.info(
                    "service_token_refresh_failed_no_cache",
                    client_id=self.client_id,
                    ex_msg=str(exc),
                    ex_type=type(exc).__name__,
                    exc_info=True,
                )
                raise ServiceTokenUnavailableError(
                    f"Unable to obtain service token for {self.client_id!r}"
                ) from exc
        return self._token

    async def aget_token(self) -> str:
        """Async convenience wrapper — runs :meth:`get_token` in a worker thread.

        FastAPI endpoints that construct their own outbound calls may
        prefer this so they don't block the event loop while waiting
        for rudra.
        """
        return await asyncio.to_thread(self.get_token)

    def _refresh(self) -> None:
        """Fetch a new token from rudra. Must be called under ``self._lock``."""
        if not self.client_id or not self._client_secret:
            raise RuntimeError(
                "SERVICE_CLIENT_ID and SERVICE_CLIENT_SECRET must be set "
                "before requesting a service token"
            )
        if not self.base_url:
            raise RuntimeError("RUDRA_BASE_URL must be set to fetch service tokens")

        url = f"{self.base_url}{_TOKEN_URL_PATH}"
        logger.info("service_token_refresh_start", client_id=self.client_id, url=url)

        with httpx.Client(timeout=self.request_timeout) as client:
            resp = client.post(
                url,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self._client_secret),
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"rudra token endpoint returned {resp.status_code}: {resp.text[:200]}"
            )

        body: dict[str, Any] = resp.json()
        # Response envelope is {"data": {...}, ...} per Tolaram APIResponse.
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict) or "access_token" not in data:
            raise RuntimeError(f"Unexpected token response shape from rudra: {body!r}")

        token = str(data["access_token"])
        expires_in_raw = data.get("expires_in")
        expires_at = self._compute_expiry(token, expires_in_raw)

        self._token = token
        self._expires_at = expires_at
        logger.info(
            "service_token_refreshed",
            client_id=self.client_id,
            expires_in=int(max(0, expires_at - time.time())),
        )

    @staticmethod
    def _compute_expiry(token: str, expires_in_raw: object) -> float:
        """Derive an absolute expiry timestamp from the token or response.

        Prefers the JWT's own ``exp`` claim (authoritative); falls back
        to the ``expires_in`` seconds in the response body. Returns a
        conservative floor (``now + 60``) as a last resort so a
        malformed response can't trap us in a tight refresh loop.
        """
        try:
            claims = jwt.decode(token, options={"verify_signature": False})
            exp = claims.get("exp")
            if isinstance(exp, int | float):
                return float(exp)
        except Exception:
            pass
        if isinstance(expires_in_raw, int | float) and expires_in_raw > 0:
            return time.time() + float(expires_in_raw)
        return time.time() + 60.0

    def invalidate(self) -> None:
        """Drop the cached token so the next :meth:`get_token` refreshes."""
        with self._lock:
            self._token = ""
            self._expires_at = 0.0


_singleton: ServiceTokenManager | None = None
_singleton_lock = threading.Lock()


def get_service_token_manager() -> ServiceTokenManager:
    """Return the process-wide :class:`ServiceTokenManager` singleton.

    The singleton is constructed on first access using Django settings.
    Tests should reset it via :func:`reset_service_token_manager`
    between cases that vary the credentials.
    """
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = ServiceTokenManager()
    return _singleton


def reset_service_token_manager() -> None:
    """Drop the process-wide singleton (test helper)."""
    global _singleton
    with _singleton_lock:
        _singleton = None
