"""Apple Sign In helper — supports web (code exchange) and mobile (id_token)."""

from __future__ import annotations

import secrets
import time
import urllib.parse
from typing import Any

import httpx
import jwt as pyjwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.conf import settings


class AppleSSO:
    """Async Apple Sign In helper.

    Web flow:  ``get_authorization_url`` → Apple posts form to callback → ``exchange_code``
    Mobile flow: ``verify_id_token`` (id_token supplied directly by the app)

    Apple uses ``response_mode=form_post`` so the callback is a POST, not a GET.

    State nonce management:
        ``get_authorization_url`` generates a server-side CSRF nonce, stores it
        in the Django cache with a 10-minute TTL, and embeds it as the ``state``
        parameter.  ``validate_and_consume_state`` checks and deletes it on
        callback — preventing OAuth2 CSRF attacks.

    JWKS caching:
        Apple public keys are cached in Redis for 6 hours to avoid a live
        HTTP round-trip on every mobile SSO call.
    """

    AUTHORIZE_URL = "https://appleid.apple.com/auth/authorize"
    TOKEN_URL = "https://appleid.apple.com/auth/token"
    JWKS_URI = "https://appleid.apple.com/auth/keys"

    _STATE_KEY_PREFIX = "sso_state:apple"
    _STATE_TTL = 600  # 10 minutes
    _JWKS_CACHE_KEY = "jwks:apple"
    _JWKS_TTL = 21600  # 6 hours

    def _client_id(self) -> str:
        """Return the Apple client (service) ID from Django settings."""
        return settings.APPLE_CLIENT_ID if hasattr(settings, "APPLE_CLIENT_ID") else ""

    def get_authorization_url(self) -> str:
        """Build the Apple authorization URL with a server-generated state nonce.

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
            "redirect_uri": settings.APPLE_REDIRECT_URI,
            "response_type": "code",
            "response_mode": "form_post",
            "scope": "email name",
            "state": nonce,
        }
        return f"{self.AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    def validate_and_consume_state(self, state: str) -> bool:
        """Validate the OAuth2 state nonce and delete it (single-use).

        Args:
            state: The ``state`` value returned by Apple in the callback.

        Returns:
            ``True`` when the nonce is valid; ``False`` when missing,
            expired, or already consumed.
        """
        from django.core.cache import cache

        key = f"{self._STATE_KEY_PREFIX}:{state}"
        value = cache.get(key)
        if value:
            cache.delete(key)
            return True
        return False

    def generate_client_secret(self) -> str:
        """Generate a short-lived ES256 client-secret JWT signed with the Apple .p8 key.

        Apple requires a freshly signed JWT (valid up to 6 months) in place of
        a static client secret.  The key is read from ``settings.APPLE_PRIVATE_KEY``
        in PEM format.

        Returns:
            Signed ES256 JWT string to use as the ``client_secret`` parameter
            in token-exchange requests.

        Raises:
            ValueError: If ``APPLE_PRIVATE_KEY`` is not configured in settings.
        """
        private_key_pem = settings.APPLE_PRIVATE_KEY
        if not private_key_pem:
            raise ValueError("APPLE_PRIVATE_KEY is not configured")

        private_key = load_pem_private_key(
            (
                private_key_pem.encode()
                if isinstance(private_key_pem, str)
                else private_key_pem
            ),
            password=None,
        )

        now = int(time.time())
        payload = {
            "iss": settings.APPLE_TEAM_ID,
            "iat": now,
            "exp": now + 86400 * 180,  # max 6 months
            "aud": "https://appleid.apple.com",
            "sub": self._client_id(),
        }
        headers = {"kid": settings.APPLE_KEY_ID, "alg": "ES256"}
        return pyjwt.encode(payload, private_key, algorithm="ES256", headers=headers)

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange an Apple authorization code for access and ID tokens.

        Args:
            code: Short-lived authorization code received in the Apple callback.
            redirect_uri: The redirect URI registered for this application.

        Returns:
            Token response dict from Apple containing ``access_token``,
            ``id_token``, ``token_type``, and ``expires_in`` fields.

        Raises:
            httpx.HTTPStatusError: If the Apple token endpoint returns a
                non-2xx status code.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self._client_id(),
                    "client_secret": self.generate_client_secret(),
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def _get_jwks(self) -> list[dict[str, Any]]:
        """Return Apple's JWKS public keys, using a Redis cache to avoid live fetches.

        Keys are cached for 6 hours.  On cache miss the keys are fetched fresh
        from Apple and re-cached.

        Returns:
            List of JWK key dicts from Apple's JWKS endpoint.
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
        """Verify an Apple id_token using cached JWKS public keys.

        Returns the decoded payload with at least ``sub`` and ``email``.

        Args:
            id_token: The raw Apple id_token JWT string.

        Returns:
            Decoded JWT payload dict.

        Raises:
            ValueError: If no matching public key is found for the token's ``kid``.
            pyjwt.DecodeError: If the token signature is invalid.
        """
        jwks = await self._get_jwks()

        header = pyjwt.get_unverified_header(id_token)
        kid = header.get("kid")

        public_key: Any = None
        for key_data in jwks:
            if key_data.get("kid") == kid:
                public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key_data)
                break

        if public_key is None:
            # Cache may be stale — bust it and retry once
            from django.core.cache import cache

            cache.delete(self._JWKS_CACHE_KEY)
            jwks = await self._get_jwks()
            for key_data in jwks:
                if key_data.get("kid") == kid:
                    public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key_data)
                    break

        if public_key is None:
            raise ValueError("Unable to find matching public key for Apple id_token")

        payload: dict[str, Any] = pyjwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=self._client_id(),
        )
        return payload


apple_sso = AppleSSO()
