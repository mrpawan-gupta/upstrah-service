"""Microservice event dispatch framework.

Provides a base :class:`ServiceDispatcher` with circuit-breaker-backed
fire-and-forget POST logic, plus concrete dispatchers for each downstream
microservice:

* :class:`KriyaDispatcher`  — webhook fan-out via kriya-service.
* :class:`RudraDispatcher`  — identity / user / company calls to rudra-service.
* :class:`VmsDispatcher`    — vehicle catalogue calls to vms-service.
* :class:`CareDispatcher`   — insurance core API calls to CARE.
* :class:`DharmaDispatcher` — claims lifecycle calls to dharma-service.
* :class:`LekhaDispatcher`  — survey document / OCR calls to lekha-service.
* :class:`AngadDispatcher`  — representative booking / inspection calls to angad-service.
* :class:`MayaDispatcher`   — agentic AI orchestration calls to maya-service.
* :class:`KuberDispatcher`  — payments gateway calls to kuber-service.
* :class:`NaradDispatcher`  — notification delivery calls to narad-service.

All dispatchers route through :class:`~common.services.HttpClient`
(lazy singleton per service) with circuit breaker protection.  Transport
failures and circuit-open rejections are logged but never raised.

Outbound authentication
-----------------------

Every request carries a bearer token:

* If the caller is handling an inbound request with a user JWT, the
  middleware has populated ``user_token_var`` and the dispatcher
  forwards that token verbatim so downstream services see the
  original end-user identity (on-behalf-of propagation).
* Otherwise (Celery tasks, startup jobs, fan-outs) the dispatcher
  fetches a short-lived service token from
  :class:`~common.auth.service_token.ServiceTokenManager` and attaches
  it instead.

The legacy ``X-Internal-Token`` shared secret has been removed. Every
downstream service now authenticates via standard RS256 JWTs.

Configuration (Django settings / env vars):

* ``KRIYA_BASE_URL``          — Base URL of kriya-service (default ``http://localhost:8002``).
* ``RUDRA_BASE_URL``          — Base URL of rudra-service (default ``http://localhost:8001``).
* ``VMS_BASE_URL``            — Base URL of vms-service (default ``http://localhost:8004``).
* ``CARE_API_URL``            — Base URL of the CARE insurance API.
* ``DHARMA_BASE_URL``         — Base URL of dharma-service (default ``http://localhost:8003``).
* ``LEKHA_BASE_URL``          — Base URL of lekha-service (default ``http://localhost:8004``).
* ``ANGAD_BASE_URL``          — Base URL of angad-service (default ``http://localhost:8004``).
* ``MAYA_BASE_URL``           — Base URL of maya-service (default ``http://localhost:8007``).
* ``KUBER_BASE_URL``          — Base URL of kuber-service (default ``http://localhost:8008``).
* ``NARAD_BASE_URL``          — Base URL of narad-service (default ``http://localhost:8009``).
* ``SERVICE_CLIENT_ID``       — This service's OAuth2 client_id.
* ``SERVICE_CLIENT_SECRET``   — This service's OAuth2 client secret.
"""

from __future__ import annotations

import contextlib
from typing import Any

import httpx
import structlog
from django.conf import settings

from common.auth.service_token import (
    ServiceTokenUnavailableError,
    get_service_token_manager,
)
from common.context import get_correlation_id, get_trace_id, get_user_token
from common.exceptions.exceptions import ExternalServiceError
from common.resilience import CircuitBreakerOpenError
from common.services import HttpClient

logger = structlog.get_logger(__name__)


class ServiceDispatcher:
    """Base fire-and-forget dispatcher for downstream microservices.

    Subclasses configure the target service by setting class attributes and
    may add domain-specific dispatch methods.  The base class provides:

    * Lazy :class:`HttpClient` singleton (with circuit breaker).
    * :meth:`_post` — fire-and-forget POST that catches all errors.
    * Structured logging for every outcome (success / non-2xx / CB open / error).

    Class Attributes:
        service_name: Identifier used for logging and the CB singleton key.
        _settings_key: Django settings attribute holding the base URL.
        _default_base_url: Fallback when the setting is absent.
        _default_timeout: HTTP timeout in seconds.
        _failure_threshold: CB consecutive failures before opening.
        _recovery_timeout: CB seconds in open state before probing.
    """

    service_name: str = ""
    _settings_key: str = ""
    _default_base_url: str = ""
    _default_timeout: float = 5.0
    _failure_threshold: int = 5
    _recovery_timeout: float = 60.0

    def _base_url(self) -> str:
        """Resolve the base URL from Django settings or the class default.

        Returns:
            Base URL string without a trailing slash.
        """
        return getattr(settings, self._settings_key, self._default_base_url).rstrip("/")

    def _client(self) -> HttpClient:
        """Return the lazy-singleton :class:`HttpClient` for this service.

        Returns:
            Configured ``HttpClient`` instance.
        """
        return HttpClient.get_instance(
            name=self.service_name,
            base_url=self._base_url(),
            timeout=self._default_timeout,
            failure_threshold=self._failure_threshold,
            recovery_timeout=self._recovery_timeout,
        )

    def _default_headers(self) -> dict[str, str]:
        """Build the header set attached to every outbound request.

        Priority for ``Authorization``:

        1. A forwarded **user bearer token** from ``user_token_var`` —
           set by the inbound-request middleware so care → kriya and
           similar fan-outs preserve the original user's identity.
        2. A **service token** from the process-wide
           :class:`ServiceTokenManager` — used for Celery tasks,
           signals, and any other path with no user in context.

        The ``X-Service-Identity`` header stamps which caller issued
        the request; it is informational only (audit / logging) and
        MUST NOT be used for authorisation decisions.

        Returns:
            Header dict with ``Authorization``, ``X-Trace-ID``,
            ``X-Correlation-ID``, and ``X-Service-Identity`` populated.
            ``Authorization`` is omitted when neither a user nor a
            service token is available (fire-and-forget callers
            tolerate the downstream 401 so the pipeline stays online
            even when rudra is briefly unreachable at startup).
        """
        headers: dict[str, str] = {
            "X-Trace-ID": get_trace_id(),
            "X-Correlation-ID": get_correlation_id(),
            "X-Service-Identity": getattr(settings, "SERVICE_CLIENT_ID", ""),
        }

        user_token = get_user_token()
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"
            return headers

        try:
            svc_token = get_service_token_manager().get_token()
        except ServiceTokenUnavailableError as exc:
            # Fire-and-forget callers swallow this via contextlib.suppress
            # in ``_post``. Log once per miss so operators see the issue.
            logger.info(
                f"{self.service_name}_service_token_unavailable",
                service=self.service_name,
                ex_msg=str(exc),
                ex_type=type(exc).__name__,
                exc_info=True,
            )
            return headers

        headers["Authorization"] = f"Bearer {svc_token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request and return the parsed JSON response.

        Handles every failure mode and wraps them in domain exceptions:

        * **Circuit open** → ``CircuitBreakerOpenError`` (503, re-raised as-is).
        * **Connection / DNS error** → ``ExternalServiceError`` (502).
        * **Timeout** → ``ExternalServiceError`` (504).
        * **Non-2xx response** → ``ExternalServiceError`` (502).
        * **JSON decode failure** → ``ExternalServiceError`` (502).

        Args:
            method: HTTP method (``GET``, ``POST``, etc.).
            path: Endpoint path relative to the service base URL.
            json: JSON body dict (for POST/PUT/PATCH).
            params: URL query parameters (for GET).
            extra_headers: Merged on top of :meth:`_default_headers`.
            timeout: Per-request timeout override (seconds).

        Returns:
            Parsed JSON response dict.

        Raises:
            CircuitBreakerOpenError: When the circuit is open (HTTP 503).
            ExternalServiceError: On transport, non-2xx, or JSON decode errors.
        """
        headers = self._default_headers()
        if extra_headers:
            headers.update(extra_headers)

        try:
            resp = self._client().request(
                method,
                path,
                json=json,
                params=params,
                headers=headers,
                timeout=timeout,
            )
        except CircuitBreakerOpenError:
            logger.info(
                f"{self.service_name}_circuit_open",
                method=method,
                path=path,
                service=self.service_name,
            )
            raise
        except httpx.TimeoutException as exc:
            logger.info(
                f"{self.service_name}_timeout",
                method=method,
                path=path,
                ex_msg=str(exc),
                ex_type=type(exc).__name__,
                exc_info=True,
            )
            raise ExternalServiceError(
                f"{self.service_name} request timed out: {method} {path}",
            )
        except httpx.ConnectError as exc:
            logger.info(
                f"{self.service_name}_connection_error",
                method=method,
                path=path,
                ex_msg=str(exc),
                ex_type=type(exc).__name__,
                exc_info=True,
            )
            raise ExternalServiceError(
                f"Failed to connect to {self.service_name}: {exc}",
            )
        except httpx.RequestError as exc:
            logger.info(
                f"{self.service_name}_request_error",
                method=method,
                path=path,
                ex_msg=str(exc),
                ex_type=type(exc).__name__,
                exc_info=True,
            )
            raise ExternalServiceError(
                f"{self.service_name} request failed: {exc}",
            )

        if resp.status_code not in (200, 201, 202):
            logger.info(
                f"{self.service_name}_non_2xx",
                method=method,
                path=path,
                status=resp.status_code,
                body=resp.text[:200],
            )
            raise ExternalServiceError(
                f"{self.service_name} {method} {path} returned {resp.status_code}",
            )

        try:
            return resp.json()
        except ValueError as exc:
            logger.info(
                f"{self.service_name}_json_decode_error",
                method=method,
                path=path,
                status=resp.status_code,
                body=resp.text[:200],
                ex_msg=str(exc),
                ex_type=type(exc).__name__,
                exc_info=True,
            )
            raise ExternalServiceError(
                f"{self.service_name} returned invalid JSON for {method} {path}",
            )

    def _get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """GET and return parsed JSON. See :meth:`_request` for full signature."""
        return self._request("GET", path, **kwargs)

    def _put(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """PUT and return parsed JSON. See :meth:`_request` for full signature."""
        return self._request("PUT", path, **kwargs)

    def _patch(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """PATCH and return parsed JSON. See :meth:`_request` for full signature."""
        return self._request("PATCH", path, **kwargs)

    def _delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """DELETE and return parsed JSON. See :meth:`_request` for full signature."""
        return self._request("DELETE", path, **kwargs)

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        event_type: str = "",
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        """Fire-and-forget POST — delegates to :meth:`_request`, swallows all errors.

        Args:
            path: Endpoint path relative to the service base URL.
            payload: JSON body dict.
            event_type: Descriptive label included in log entries.
            extra_headers: Merged on top of :meth:`_default_headers`.
        """
        with contextlib.suppress(Exception):
            self._request("POST", path, json=payload, extra_headers=extra_headers)


class KriyaDispatcher(ServiceDispatcher):
    """Dispatcher for kriya-service (webhook fan-out).

    Provides two public methods matching the two Kriya inbound endpoints:

    * :meth:`dispatch_webhook` — generic IDV catalogue events.
    * :meth:`dispatch_policy_event` — typed policy lifecycle events.
    """

    service_name = "kriya"
    _settings_key = "KRIYA_BASE_URL"
    _default_base_url = "http://localhost:8002"
    _default_timeout = 2.0
    _failure_threshold = 5
    _recovery_timeout = 30.0

    _IDV_EVENTS_PATH = "/webhook/api/v1/idv-events"
    _POLICY_EVENTS_PATH = "/webhook/api/v1/policy-events"
    _BOOKING_EVENTS_PATH = "/webhook/api/v1/booking-events"

    def dispatch_idv_event(self, **kwargs: Any) -> None:
        """Forward an IDV lifecycle event to kriya-service.

        Keyword Args:
            resource_type: Short identifier (e.g. ``"vehicle_make"``).
            resource_id: Internal PK of the catalogue resource.
            action: One of ``"created"``, ``"updated"``, ``"deleted"``, ``"synced"``.
            company_id: Owning company PK.
            model_data: Serialised model dict (from ``instance.to_dict()``).
            external_id: Company's own identifier for this resource.
            junction_id: PK of the company junction record.
        """
        resource_type: str = kwargs["resource_type"]
        resource_id: int | str | None = kwargs.get("resource_id")
        action: str = kwargs["action"]
        company_id: int | None = kwargs.get("company_id")
        model_data: dict[str, Any] = kwargs.get("model_data", {})
        external_id: str = kwargs.get("external_id", "")
        junction_id: int | None = kwargs.get("junction_id")

        event_type = f"idv.{resource_type}.{action}"

        payload = {
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "company_id": company_id,
            "model_data": model_data,
            "external_id": external_id,
            "junction_id": junction_id,
        }

        self._post(self._IDV_EVENTS_PATH, payload, event_type=event_type)

        logger.info(
            "kriya_dispatch_sent",
            event_type=event_type,
            resource_id=resource_id,
            junction_id=junction_id,
            company_id=company_id,
            external_id=external_id or None,
        )

    def dispatch_policy_event(self, **kwargs: Any) -> None:
        """Forward a policy lifecycle event to Kriya's policy-events endpoint.

        Keyword Args:
            action: Dot-separated workflow and outcome — e.g.
                ``"creation.completed"``, ``"creation.failed"``.
            draft_id: Primary key of the ``PolicyDraft`` record.
            company_id: Rudra company ID that owns this policy draft.
            policy_number: CARE policy number on success; ``None`` on failure.
            pid: CARE internal PID on success; ``None`` on failure.
            owner_care_id: CARE user ID of the policy owner; ``None`` on failure.
            status: Outcome status string — ``"completed"`` or ``"failed"``.
            error: Human-readable error on failure; ``None`` on success.
            extra: Optional extra fields merged into the webhook ``data`` payload.
        """
        action: str = kwargs["action"]
        draft_id: int = kwargs["draft_id"]
        company_id: int = kwargs["company_id"]

        event_type = f"policy.{action}"

        payload = {
            "event_type": event_type,
            "company_id": company_id,
            "draft_id": draft_id,
            "policy_number": kwargs.get("policy_number"),
            "pid": kwargs.get("pid"),
            "owner_care_id": kwargs.get("owner_care_id"),
            "status": kwargs.get("status", "completed"),
            "error": kwargs.get("error"),
            "extra": kwargs.get("extra") or {},
        }

        self._post(self._POLICY_EVENTS_PATH, payload, event_type=event_type)

        logger.info(
            "kriya_policy_event_sent",
            event_type=event_type,
            draft_id=draft_id,
            company_id=company_id,
        )

    def dispatch_booking_event(self, **kwargs: Any) -> None:
        """Forward a booking lifecycle event to kriya-service.

        Emits ``booking.<resource_type>.<action>`` — used by angad-service
        for per-company catalogue junction changes
        (``company_appointment_type``, ``company_time_slot``,
        ``company_cancellation_reason``, ``company_skip_reason``,
        ``company_holiday``) and for representative booking / item
        transitions.

        Keyword Args:
            resource_type: Short identifier
                (e.g. ``"company_appointment_type"``, ``"booking"``).
            resource_id: Internal PK of the affected resource.
            action: One of ``"created"``, ``"updated"``, ``"deleted"``,
                ``"synced"``.
            company_id: Owning company PK.
            model_data: Serialised model dict (from ``instance.to_dict()``).
            external_id: Company's own identifier for this resource
                (junction rows only).
            junction_id: PK of the company junction record (junction
                events only).
        """
        resource_type: str = kwargs["resource_type"]
        resource_id: int | str | None = kwargs.get("resource_id")
        action: str = kwargs["action"]
        company_id: int | None = kwargs.get("company_id")
        model_data: dict[str, Any] = kwargs.get("model_data", {})
        external_id: str = kwargs.get("external_id", "")
        junction_id: int | None = kwargs.get("junction_id")

        event_type = f"booking.{resource_type}.{action}"

        payload = {
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "company_id": company_id,
            "model_data": model_data,
            "external_id": external_id,
            "junction_id": junction_id,
        }

        self._post(self._BOOKING_EVENTS_PATH, payload, event_type=event_type)

        logger.info(
            "kriya_booking_event_sent",
            event_type=event_type,
            resource_id=resource_id,
            junction_id=junction_id,
            company_id=company_id,
            external_id=external_id or None,
        )


class RudraDispatcher(ServiceDispatcher):
    """Dispatcher for rudra-service (identity / user / company management).

    Rudra is the central identity provider — it issues JWTs, manages users,
    companies, and tenancy.
    """

    service_name = "rudra"
    _settings_key = "RUDRA_BASE_URL"
    _default_base_url = "http://localhost:8001"
    _default_timeout = 5.0
    _failure_threshold = 5
    _recovery_timeout = 30.0

    _COMPANIES_PATH = "/accounts/api/v1/companies"
    _USERS_PATH = "/accounts/api/v1/users"

    def fetch_companies(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch the list of companies from rudra-service.

        Keyword Args:
            Any query parameters forwarded to the companies endpoint
            (e.g. ``is_active=True``, ``limit=50``, ``offset=0``).

        Returns:
            Parsed JSON response dict from rudra-service.

        Raises:
            ExternalServiceError: On non-2xx status or transport failure.
            CircuitBreakerOpenError: If the circuit is open.
        """
        return self._get(self._COMPANIES_PATH, params=kwargs or None)

    def fetch_users(self, *, ids: list[int]) -> dict[str, Any]:
        """Fetch user rows for *ids* via the listing endpoint (``?ids=``).

        Bulk identity lookup used by peers to enrich their own rows with a
        user's display name in a single round-trip (rather than one call per
        row). Resolves against ``GET /users`` filtered to the requested PKs;
        each item carries ``full_name`` for direct display. The caller's user
        token is forwarded when a request context exists; otherwise a service
        token is minted — ``/users`` accepts either.

        Args:
            ids: rudra user PKs to resolve. An empty list returns an empty
                ``data`` array. Batch ≤200 IDs per call (the listing page cap).

        Returns:
            Parsed JSON envelope from rudra-service; ``data`` is a list of
            ``UserListItemSchema`` dicts (includes ``id`` and ``full_name``).

        Raises:
            ExternalServiceError: On non-2xx status or transport failure.
            CircuitBreakerOpenError: If the circuit is open.
        """
        if not ids:
            return {"data": []}
        return self._get(
            self._USERS_PATH, params={"ids": ids, "limit": min(len(ids), 200)}
        )


class VmsDispatcher(ServiceDispatcher):
    """Dispatcher for vms-service (vehicle management / IDV catalogue).

    VMS owns the canonical vehicle catalogue data (makes, models, variants)
    and IDV pricing.  Use this dispatcher for outbound calls to vms-service.
    """

    service_name = "vms"
    _settings_key = "VMS_BASE_URL"
    _default_base_url = "http://localhost:8004"
    _default_timeout = 5.0
    _failure_threshold = 5
    _recovery_timeout = 30.0


class CareDispatcher(ServiceDispatcher):
    """Dispatcher for the CARE insurance core API.

    CARE is the external insurer system handling policy lifecycle
    (save, submit, cancel, validate).  Longer timeout to accommodate
    CARE's response latency.
    """

    service_name = "care"
    _settings_key = "CARE_API_URL"
    _default_base_url = ""
    _default_timeout = 30.0
    _failure_threshold = 3
    _recovery_timeout = 60.0


class DharmaDispatcher(ServiceDispatcher):
    """Dispatcher for dharma-service (claims lifecycle).

    Dharma owns the claims lifecycle — intake, assessment, settlement.
    Other services forward claim events (e.g. submitted inspection
    updates from angad-service) to dharma through this dispatcher.
    """

    service_name = "dharma"
    _settings_key = "DHARMA_BASE_URL"
    _default_base_url = "http://localhost:8003"
    _default_timeout = 5.0
    _failure_threshold = 5
    _recovery_timeout = 30.0


class LekhaDispatcher(ServiceDispatcher):
    """Dispatcher for lekha-service (survey documents & OCR).

    Lekha manages survey document intake, storage, and OCR-extracted
    metadata. Use this dispatcher for outbound calls to lekha-service.
    """

    service_name = "lekha"
    _settings_key = "LEKHA_BASE_URL"
    _default_base_url = "http://localhost:8004"
    _default_timeout = 5.0
    _failure_threshold = 5
    _recovery_timeout = 30.0


class AngadDispatcher(ServiceDispatcher):
    """Dispatcher for angad-service (representative booking & inspection).

    Angad owns field-representative bookings and the inspection
    updates reps record. Other services query bookings / inspection
    status through this dispatcher.
    """

    service_name = "angad"
    _settings_key = "ANGAD_BASE_URL"
    _default_base_url = "http://localhost:8004"
    _default_timeout = 5.0
    _failure_threshold = 5
    _recovery_timeout = 30.0

    _REPRESENTATIVES_PATH = "/representative/api/v1/representatives"
    _REPRESENTATIVE_DEACTIVATE_PATH = (
        "/representative/api/v1/representatives/deactivate"
    )

    def create_representative(self, *, user_id: int) -> dict[str, Any]:
        """Create a field representative for *user_id*.

        Unlike :meth:`_post` (fire-and-forget, swallows everything), this
        **raises** on failure so the calling Celery task can retry. angad
        de-duplicates on ``user_id`` — including soft-deleted rows — so a
        retry never creates a duplicate; it returns the existing
        representative.

        Args:
            user_id: rudra user PK to register as a representative.

        Returns:
            Parsed JSON response from angad-service.

        Raises:
            ExternalServiceError: Transport, non-2xx, or JSON decode error.
            CircuitBreakerOpenError: When angad's circuit is open.
        """
        return self._request(
            "POST",
            self._REPRESENTATIVES_PATH,
            json={"user_id": user_id},
        )

    def deactivate_representative(self, *, user_id: int) -> dict[str, Any]:
        """Deactivate the field representative for *user_id*.

        The inverse of :meth:`create_representative`, called when the
        Representative group is removed from a user. Like that method this
        **raises** on failure so the calling Celery task can retry. angad
        deactivation is idempotent — an absent representative is a no-op and
        re-deactivating an inactive rep changes nothing — so a retry is safe.

        Args:
            user_id: rudra user PK whose representative should be deactivated.

        Returns:
            Parsed JSON response from angad-service.

        Raises:
            ExternalServiceError: Transport, non-2xx, or JSON decode error.
            CircuitBreakerOpenError: When angad's circuit is open.
        """
        return self._request(
            "POST",
            self._REPRESENTATIVE_DEACTIVATE_PATH,
            json={"user_id": user_id},
        )


class MayaDispatcher(ServiceDispatcher):
    """Dispatcher for maya-service (agentic AI orchestration).

    Maya owns LLM-backed agents for document analysis, quote
    recommendations, and policy Q&A. Longer timeout to accommodate
    agent reasoning latency.
    """

    service_name = "maya"
    _settings_key = "MAYA_BASE_URL"
    _default_base_url = "http://localhost:8007"
    _default_timeout = 30.0
    _failure_threshold = 3
    _recovery_timeout = 60.0


class KuberDispatcher(ServiceDispatcher):
    """Dispatcher for kuber-service (payments gateway).

    Kuber processes premium payments and manages transaction lifecycle.
    """

    service_name = "kuber"
    _settings_key = "KUBER_BASE_URL"
    _default_base_url = "http://localhost:8008"
    _default_timeout = 10.0
    _failure_threshold = 5
    _recovery_timeout = 60.0


class NaradDispatcher(ServiceDispatcher):
    """Dispatcher for narad-service (notification delivery).

    Narad dispatches email, SMS, push, and in-app notifications.
    """

    service_name = "narad"
    _settings_key = "NARAD_BASE_URL"
    _default_base_url = "http://localhost:8009"
    _default_timeout = 5.0
    _failure_threshold = 5
    _recovery_timeout = 30.0


_kriya = KriyaDispatcher()
_rudra = RudraDispatcher()
_vms = VmsDispatcher()
_care = CareDispatcher()
_dharma = DharmaDispatcher()
_lekha = LekhaDispatcher()
_angad = AngadDispatcher()
_maya = MayaDispatcher()
_kuber = KuberDispatcher()
_narad = NaradDispatcher()
