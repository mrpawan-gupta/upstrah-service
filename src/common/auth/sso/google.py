"""Google OAuth2 helper — supports both web (code exchange) and mobile (id_token)."""

from __future__ import annotations

import secrets
import urllib.parse
from typing import Any

import httpx
import jwt as pyjwt
from django.conf import settings


class GoogleSSO:
    """Async Google OAuth2 helper.

    Web flow:  ``get_authorization_url`` → redirect → ``exchange_code`` + ``get_user_info``
    Mobile flow: ``verify_id_token`` (id_token supplied directly by the app)

    State nonce management:
        ``get_authorization_url`` generates a server-side CSRF nonce, stores it
        in the Django cache with a 10-minute TTL, and embeds it as the ``state``
        parameter.  ``validate_and_consume_state`` checks and deletes it on
        callback — preventing OAuth2 CSRF attacks.

    JWKS caching:
        Google public keys (used for id_token verification) are cached in
        Redis for 6 hours to avoid a live HTTP round-trip on every mobile
        SSO call.
    """

    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"

    _STATE_KEY_PREFIX = "sso_state:google"
    _STATE_TTL = 600  # 10 minutes
    _JWKS_CACHE_KEY = "jwks:google"
    _JWKS_TTL = 21600  # 6 hours

    def _client_id(self) -> str:
        """Return the Google OAuth2 client ID from Django settings."""
        return settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"]

    def _client_secret(self) -> str:
        """Return the Google OAuth2 client secret from Django settings."""
        return settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["secret"]

    def get_authorization_url(self) -> str:
        """Build the Google OAuth2 authorization URL with a server-generated state nonce.

        Generates a cryptographically random nonce, stores it in the Django
        cache with a 10-minute TTL, and embeds it as the ``state`` parameter.
        The callback must call :meth:`validate_and_consume_state` to prevent
        OAuth2 CSRF attacks.

        Returns:
            Full authorization URL string to redirect the user's browser to.
        """
        from django.core.cache import cache

        nonce = secrets.token_urlsafe(32)
        cache.set(f"{self._STATE_KEY_PREFIX}:{nonce}", "1", timeout=self._STATE_TTL)
        params = {
            "client_id": self._client_id(),
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": nonce,
            "access_type": "offline",
        }
        return f"{self.AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    def validate_and_consume_state(self, state: str) -> bool:
        """Validate the OAuth2 state nonce and delete it (single-use).

        Args:
            state: The ``state`` value returned by Google in the callback.

        Returns:
            ``True`` when the nonce is valid; ``False`` when it is missing,
            expired, or has already been consumed.
        """
        from django.core.cache import cache

        key = f"{self._STATE_KEY_PREFIX}:{state}"
        value = cache.get(key)
        if value:
            cache.delete(key)
            return True
        return False

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange a Google authorization code for access and ID tokens.

        Args:
            code: Short-lived authorization code received in the OAuth2 callback.
            redirect_uri: The redirect URI registered for this application.

        Returns:
            Token response dict from Google containing ``access_token``,
            ``id_token``, ``token_type``, and ``expires_in`` fields.

        Raises:
            httpx.HTTPStatusError: If the Google token endpoint returns a
                non-2xx status code.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._client_id(),
                    "client_secret": self._client_secret(),
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Fetch user profile information from Google using an access token.

        Calls the Google ``/oauth2/v3/userinfo`` endpoint with the supplied
        bearer token.

        Args:
            access_token: OAuth2 access token obtained via :meth:`exchange_code`.

        Returns:
            User-info dict containing at least ``sub``, ``email``, ``name``,
            and ``picture`` fields.

        Raises:
            httpx.HTTPStatusError: If the userinfo endpoint returns a non-2xx
                status code.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def _get_jwks(self) -> list[dict[str, Any]]:
        """Return Google's JWKS public keys, using a Redis cache to avoid live fetches.

        Keys are cached for 6 hours.  On cache miss (or if Redis is down) the
        keys are fetched fresh from Google and re-cached.

        Returns:
            List of JWK key dicts from Google's JWKS endpoint.
        """
        from django.core.cache import cache

        cached: list[dict[str, Any]] | None = cache.get(self._JWKS_CACHE_KEY)
        if cached is not None:
            return cached

        async with httpx.AsyncClient() as client:
            resp = await client.get(self.JWKS_URI)
            resp.raise_for_status()
            keys: list[dict[str, Any]] = resp.json().get("keys", [])

        import contextlib

        with contextlib.suppress(Exception):
            cache.set(self._JWKS_CACHE_KEY, keys, timeout=self._JWKS_TTL)
        return keys

    async def verify_id_token(self, id_token: str) -> dict[str, Any]:
        """Verify a Google id_token using cached JWKS public keys.

        Returns the decoded payload with at least ``sub``, ``email``, ``name``.

        Args:
            id_token: The raw Google id_token JWT string.

        Returns:
            Decoded JWT payload dict.

        Raises:
            ValueError: If no matching public key is found for the token's ``kid``.
            pyjwt.DecodeError: If the token signature is invalid.
        """
        jwks = await self._get_jwks()

        header = pyjwt.get_unverified_header(id_token)
        kid = header.get("kid")

        public_key: pyjwt.algorithms.RSAAlgorithm | None = None
        for key_data in jwks:
            if key_data.get("kid") == kid:
                public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key_data)  # type: ignore[assignment]
                break

        if public_key is None:
            # Cache may be stale — bust it and retry once
            from django.core.cache import cache

            cache.delete(self._JWKS_CACHE_KEY)
            jwks = await self._get_jwks()
            for key_data in jwks:
                if key_data.get("kid") == kid:
                    public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key_data)  # type: ignore[assignment]
                    break

        if public_key is None:
            raise ValueError("Unable to find matching public key for id_token")

        payload: dict[str, Any] = pyjwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=self._client_id(),
        )
        return payload


google_sso = GoogleSSO()
