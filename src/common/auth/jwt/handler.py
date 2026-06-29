"""JWT token creation, verification, and revocation for Rudra auth service.

Provides :class:`JWTHandler` — a singleton that wraps PyJWT to issue
RS256 tokens, store revoked JTIs in the Django cache (backed by Redis
at runtime), and verify tokens on each request.

Three token types are minted, all signed with the same RSA private key
and verifiable with the same public key:

* ``token_type="access"`` — end-user access token (60 min default)
* ``token_type="service"`` — internal service-to-service token
  (15 min default, issued via client_credentials to a ``ServiceClient``)
* ``token_type="partner"`` — external partner token (30 min default,
  issued via client_credentials to a ``CompanyApiCredential``; carries
  the partner's ``company_id`` and an optional ``on_behalf_of`` user id
  plus an RFC 8693 ``act`` claim)

Additionally, refresh tokens (``token_type="refresh"``) rotate the user
access token without a credentials re-challenge.

All issued tokens carry ``iss="rudra-service"`` and
``aud="<JWT_EXPECTED_AUDIENCE>"`` (default ``"tolaram"``) so downstream
services can reject tokens meant for a different platform.

Access tokens include ``is_superuser`` and ``is_staff`` claims so that
downstream services (e.g. VMS) can authorise requests without a DB lookup.

The global singleton :data:`jwt_handler` is the only instance that should
be used throughout the codebase.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Never

import jwt
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from django.conf import settings
from jwt.algorithms import RSAAlgorithm


class JWTHandler:
    """RS256 JWT token handler for Rudra auth service authentication.

    Wraps PyJWT to issue short-lived access tokens and long-lived refresh
    tokens, verify tokens on each request (including blacklist checks via the
    Django cache), and revoke individual tokens by their ``jti`` claim.

    Signing uses ``JWT_PRIVATE_KEY``; verification uses ``JWT_PUBLIC_KEY``.
    Both must be set in non-DEBUG environments.

    The global singleton :data:`jwt_handler` at module level should be used
    throughout the codebase; do not construct additional instances.

    Attributes:
        secret_key: RSA private key PEM read from ``settings.JWT_PRIVATE_KEY``.
        algorithm: JWT algorithm; defaults to ``"RS256"``.
        access_token_expire: Access token lifetime in minutes (default 60).
        refresh_token_expire: Refresh token lifetime in days (default 7).
    """

    def __init__(self) -> None:
        """Initialise the handler, reading JWT config from Django settings."""
        self.secret_key: str = settings.JWT_PRIVATE_KEY
        self.algorithm: str = getattr(settings, "JWT_ALGORITHM", "RS256")
        self.key_id: str = getattr(settings, "JWT_KEY_ID", "default")
        self.access_token_expire: int = getattr(
            settings,
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
            60,
        )
        self.refresh_token_expire: int = getattr(
            settings,
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
            7,
        )
        self.service_token_expire: int = getattr(
            settings,
            "JWT_SERVICE_TOKEN_EXPIRE_MINUTES",
            15,
        )
        self.partner_token_expire: int = getattr(
            settings,
            "JWT_PARTNER_TOKEN_EXPIRE_MINUTES",
            30,
        )
        self.issuer: str = getattr(settings, "JWT_ISSUER", "rudra-service")
        self.audience: str = getattr(settings, "JWT_EXPECTED_AUDIENCE", "tolaram")
        self._public_key: str = getattr(settings, "JWT_PUBLIC_KEY", "").replace(
            "\\n", "\n"
        )
        # Lazily-computed JWK cache; populated on first /.well-known/jwks.json
        # request. A single-key rotation invalidates this by restarting the
        # process (rotation-via-kid requires a reload today).
        self._jwk_cache: dict[str, Any] | None = None

    def generate_access_token(
        self,
        user_id: str,
        user_data: dict[str, Any] | None = None,
    ) -> str:
        """Generate a signed JWT access token for the given user.

        The token includes ``user_id``, ``is_superuser``, ``is_staff``,
        ``token_type="access"``, a UUID4 ``jti`` for revocation, ``iat``,
        ``exp``, and ``iss`` claims.  Additional claims from *user_data* are
        merged into the payload — callers should pass ``is_superuser`` and
        ``is_staff`` via *user_data* so downstream services can authorise
        requests without a DB lookup.

        Args:
            user_id: Primary key of the user (stored in the ``user_id`` claim).
            user_data: Optional extra claims to merge into the payload.
                Expected keys: ``is_superuser`` (bool), ``is_staff`` (bool).

        Returns:
            Signed JWT string valid for ``access_token_expire`` minutes.
        """
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "user_id": user_id,
            "is_superuser": False,
            "is_staff": False,
            "token_type": "access",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_expire),
            "iss": self.issuer,
            "aud": self.audience,
        }
        if user_data:
            payload.update(user_data)
            # user_data must not override the subject or token_type invariants
            payload["sub"] = str(user_id)
            payload["token_type"] = "access"
        return str(jwt.encode(payload, self.secret_key, algorithm=self.algorithm))

    def generate_refresh_token(self, user_id: str) -> str:
        """Generate a signed JWT refresh token for the given user.

        Includes ``user_id``, ``token_type="refresh"``, a UUID4 ``jti``,
        ``iat``, ``exp``, and ``iss`` claims.

        Args:
            user_id: Primary key of the user.

        Returns:
            Signed JWT string valid for ``refresh_token_expire`` days.
        """
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "user_id": user_id,
            "token_type": "refresh",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(days=self.refresh_token_expire),
            "iss": self.issuer,
            "aud": self.audience,
        }
        return str(jwt.encode(payload, self.secret_key, algorithm=self.algorithm))

    def blacklist_token(self, jti: str, ttl_seconds: int) -> None:
        """Store *jti* in the blacklist cache with the token's remaining TTL."""
        from django.core.cache import cache

        cache.set(f"blacklist:{jti}", "1", timeout=ttl_seconds)

    def is_blacklisted(self, jti: str) -> bool:
        """Return ``True`` if *jti* has been blacklisted (token was revoked)."""
        from django.core.cache import cache

        return cache.get(f"blacklist:{jti}") is not None

    def verify_token(
        self,
        token: str,
        audience: str | None = None,
    ) -> dict[str, Any]:
        """Verify and decode a JWT token.

        Decodes the token using the RSA public key, enforces the ``aud``
        claim (if the handler is configured with an expected audience),
        checks expiry (handled by PyJWT), and verifies the token has not
        been blacklisted.

        Accepts all three token types minted by this handler (access,
        refresh, service, partner). Callers that need to restrict which
        ``token_type`` is permitted should inspect the returned payload
        themselves — ``verify_token`` intentionally does not enforce it so
        one verification path serves every downstream dependency.

        Args:
            token: The raw JWT string.
            audience: Override the expected ``aud`` claim. When ``None``
                (default) the handler's configured audience is used. Pass
                ``""`` to skip audience validation entirely (useful in
                tests and during very rare migration windows).

        Returns:
            The decoded payload dictionary.

        Raises:
            jwt.ExpiredSignatureError: If the token has expired or been revoked.
            jwt.InvalidAudienceError: If the ``aud`` claim is missing or wrong.
            jwt.DecodeError: If the token is malformed (missing segments, bad
                encoding, etc.).
            jwt.InvalidTokenError: For other token validation failures
                (bad signature, missing claims, etc.).
        """
        expected_audience = self.audience if audience is None else audience
        decode_kwargs: dict[str, Any] = {
            "algorithms": [self.algorithm],
            "issuer": self.issuer,
        }
        if expected_audience:
            decode_kwargs["audience"] = expected_audience
        else:
            # Disable aud validation entirely when caller explicitly opted out.
            decode_kwargs["options"] = {"verify_aud": False}

        try:
            payload: dict[str, Any] = jwt.decode(
                token, self._public_key, **decode_kwargs
            )
        except jwt.ExpiredSignatureError:
            raise jwt.ExpiredSignatureError("Token has expired")
        except jwt.InvalidAudienceError:
            raise jwt.InvalidAudienceError("Invalid audience")
        except jwt.InvalidIssuerError:
            raise jwt.InvalidIssuerError("Invalid issuer")
        except jwt.DecodeError:
            raise jwt.DecodeError("Invalid token")
        except jwt.InvalidTokenError:
            raise jwt.InvalidTokenError("Invalid token")
        except Exception as exc:
            raise jwt.DecodeError("Authentication failed") from exc

        jti = payload.get("jti", "")
        if jti and self.is_blacklisted(jti):
            raise jwt.InvalidTokenError("Token has been revoked")

        return payload

    def get_user_from_token(self, token: str) -> str | None:
        """Extract the ``user_id`` claim from a token without raising on error.

        Args:
            token: Raw JWT string to decode.

        Returns:
            The ``user_id`` claim string, or ``None`` if the token is invalid
            or lacks the claim.
        """
        try:
            payload = self.verify_token(token)
            return payload.get("user_id")
        except Exception:
            return None

    def is_token_valid(self, token: str) -> bool:
        """Return ``True`` if the token passes full verification (not expired, not blacklisted).

        Args:
            token: Raw JWT string to validate.

        Returns:
            ``True`` when the token is valid; ``False`` on any failure.
        """
        try:
            self.verify_token(token)
        except Exception:
            return False
        else:
            return True

    def generate_service_token(
        self,
        client_id: str,
        service_name: str,
        scopes: list[str] | None = None,
    ) -> str:
        """Generate a short-lived JWT for a Tolaram internal service.

        Service tokens are issued to ``ServiceClient`` rows via the
        OAuth2 ``client_credentials`` grant and replace the legacy
        ``X-Internal-Token`` shared secret. The resulting token has
        ``token_type="service"`` and carries the caller's ``client_id``
        and scope set.

        Args:
            client_id: The ``ServiceClient.client_id`` identifying the
                caller (e.g. ``"care-service"``).
            service_name: Human-readable label from
                ``ServiceClient.service_name``.
            scopes: OAuth2 scope strings granted to the caller; embedded
                verbatim on the JWT. ``None`` becomes an empty list.

        Returns:
            Signed JWT string valid for ``service_token_expire`` minutes.
        """
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": client_id,
            "token_type": "service",
            "client_id": client_id,
            "service_name": service_name,
            "scopes": list(scopes or []),
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=self.service_token_expire),
            "iss": self.issuer,
            "aud": self.audience,
        }
        return str(jwt.encode(payload, self.secret_key, algorithm=self.algorithm))

    def generate_partner_token(
        self,
        client_id: str,
        company_id: int,
        scopes: list[str] | None = None,
        on_behalf_of: str | None = None,
    ) -> str:
        """Generate a JWT for an external partner (``CompanyApiCredential``).

        Partner tokens are issued via ``client_credentials`` to a
        ``CompanyApiCredential`` owned by the partner's ``Company``. The
        token always carries the partner's ``company_id``; when
        ``on_behalf_of`` is supplied, an RFC 8693 ``act`` claim identifies
        the calling partner as the actor acting on behalf of the named
        user. Downstream services treat the token as belonging to that
        user, scoped to the partner's company.

        Args:
            client_id: The ``CompanyApiCredential.client_id``.
            company_id: The partner's ``Company.id`` (baked into the
                token so downstream services don't need to look it up).
            scopes: OAuth2 scope strings the partner may request
                (e.g. ``["policy:issue"]``). ``None`` becomes an empty list.
            on_behalf_of: Optional rudra ``User.id`` to act on behalf of.
                Callers MUST have validated that the user belongs to the
                partner's company before passing this; rudra does not
                re-check here.

        Returns:
            Signed JWT string valid for ``partner_token_expire`` minutes.
        """
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": client_id,
            "token_type": "partner",
            "client_id": client_id,
            "company_id": company_id,
            "scopes": list(scopes or []),
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=self.partner_token_expire),
            "iss": self.issuer,
            "aud": self.audience,
        }
        if on_behalf_of is not None:
            payload["on_behalf_of"] = str(on_behalf_of)
            # RFC 8693 actor claim — the partner client is acting on
            # behalf of the supplied user.
            payload["act"] = {"sub": client_id}
        return str(jwt.encode(payload, self.secret_key, algorithm=self.algorithm))

    def rotate_refresh_token(self, old_refresh_token: str, user_id: str) -> str:
        """Exchange a valid refresh token for a fresh one, blacklisting the old.

        Used by the ``/auth/refresh`` endpoint to enforce single-use
        refresh tokens. Verifies the incoming token is a non-revoked,
        non-expired refresh token for the supplied user, blacklists its
        ``jti`` for its remaining lifetime, and returns a newly-issued
        refresh token for the same user.

        Args:
            old_refresh_token: Raw JWT previously issued as
                ``token_type="refresh"``.
            user_id: Expected ``user_id`` claim. Callers pass the
                authenticated user's PK to guard against cross-user
                reuse of a leaked refresh token.

        Returns:
            Freshly-signed refresh JWT valid for ``refresh_token_expire``
            days.

        Raises:
            jwt.InvalidTokenError: The supplied token is not a refresh
                token, has a different ``user_id``, or cannot be verified.
            jwt.ExpiredSignatureError: The supplied token has expired.
        """
        payload = self.verify_token(old_refresh_token)

        if payload.get("token_type") != "refresh":
            raise jwt.InvalidTokenError("Not a refresh token")

        token_user_id = payload.get("user_id")
        if str(token_user_id) != str(user_id):
            raise jwt.InvalidTokenError("Refresh token does not match user")

        jti = payload.get("jti", "")
        exp_ts = payload.get("exp")
        if jti and isinstance(exp_ts, int | float):
            remaining = int(exp_ts - datetime.now(UTC).timestamp())
            if remaining > 0:
                self.blacklist_token(jti, ttl_seconds=remaining)

        return self.generate_refresh_token(str(user_id))

    def get_public_jwk(self) -> dict[str, Any]:
        """Return the signing public key as a JWK dict.

        The document is suitable for inclusion in a JWKS response
        (``{"keys": [jwk]}``). Downstream services fetch this via
        ``GET /.well-known/jwks.json`` and cache the result; they re-fetch
        when they encounter a ``kid`` mismatch.

        The result is cached on the instance after first computation
        (key material does not change over the lifetime of a process —
        rotation requires a restart).

        Returns:
            JWK dict with ``kid``, ``kty``, ``use``, ``alg``, ``n``, ``e``.

        Raises:
            RuntimeError: Public key has not been configured.
        """
        if self._jwk_cache is not None:
            return self._jwk_cache

        if not self._public_key:
            raise RuntimeError("JWT_PUBLIC_KEY is not configured; cannot publish JWKS")

        # RSAAlgorithm.to_jwk emits a JSON string with kty/n/e. Augment it
        # with kid/use/alg so downstream services can match tokens by kid
        # and know the signature algorithm without re-deriving.
        public_key = load_pem_public_key(self._public_key.encode())
        jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
        jwk["kid"] = self.key_id
        jwk["use"] = "sig"
        jwk["alg"] = self.algorithm
        self._jwk_cache = jwk
        return jwk

    def refresh_access_token(self, refresh_token: str) -> str | None:
        """Generate a new access token from a valid refresh token.

        Verifies the refresh token (including blacklist check), confirms
        ``token_type == "refresh"``, and issues a fresh access token for the
        same ``user_id``.

        Args:
            refresh_token: A previously issued JWT refresh token string.

        Returns:
            A new signed access token string, or ``None`` if the refresh token
            is invalid, expired, revoked, or missing the ``user_id`` claim.
        """

        def _raise_invalid_token(msg: str) -> Never:
            """Raise an invalid token error with the given message."""
            raise jwt.InvalidTokenError(msg)

        try:
            payload = self.verify_token(refresh_token)

            if payload.get("token_type") != "refresh":
                _raise_invalid_token("Invalid refresh token")

            user_id = payload.get("user_id")
            if not user_id:
                _raise_invalid_token("No user ID in refresh token")

            return self.generate_access_token(user_id)
        except Exception:
            return None


# Global JWT handler instance
jwt_handler = JWTHandler()
