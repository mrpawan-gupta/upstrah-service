"""FastAPI integration test for the phone → OTP → JWT auth flow.

Drives the real ASGI surface via ``TestClient`` against a real DB
transaction (``@pytest.mark.django_db``): send OTP → verify OTP → use the
issued access token to read ``/auth/me``. OTP delivery is mocked, and the
generated code is read back from the persisted ``OTP`` row.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from upstrah.asgi import get_application

PHONE = "+15049684139"
BASE = "/accounts/api/v1"


@pytest.fixture
def client() -> TestClient:
    """Return a ``TestClient`` wrapping a fresh FastAPI app."""
    return TestClient(get_application())


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset OTP rate/verify counters and the JWT blacklist between tests."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


def _stored_code(phone: str) -> str:
    """Read the OTP code persisted for ``phone`` straight from the DB."""
    from accounts.models import OTP

    return OTP.objects.get(phone=phone).otp


@pytest.mark.django_db(transaction=True)
def test_otp_send_verify_then_me(client: TestClient) -> None:
    """Send → verify yields a JWT pair; the access token authorises /auth/me."""
    sent = client.post(f"{BASE}/auth/otp/send", json={"phone": PHONE})
    assert sent.status_code == 200, sent.text
    assert sent.json()["data"]["expires_in"] == 600

    code = _stored_code(PHONE)
    verified = client.post(
        f"{BASE}/auth/otp/verify", json={"phone": PHONE, "code": code}
    )
    assert verified.status_code == 200, verified.text
    tokens = verified.json()["data"]
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    me = client.get(
        f"{BASE}/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200, me.text
    body = me.json()["data"]
    assert body["phone"] == PHONE
    assert body["profile"]["role"] is None


@pytest.mark.django_db(transaction=True)
def test_verify_rejects_bad_code(client: TestClient) -> None:
    """A wrong OTP code is rejected with a 401 (AuthenticationError)."""
    client.post(f"{BASE}/auth/otp/send", json={"phone": PHONE})
    verified = client.post(
        f"{BASE}/auth/otp/verify", json={"phone": PHONE, "code": "9999"}
    )
    assert verified.status_code == 401, verified.text


@pytest.mark.django_db(transaction=True)
def test_refresh_issues_new_access_token(client: TestClient) -> None:
    """A valid refresh token is exchanged for a fresh token pair."""
    client.post(f"{BASE}/auth/otp/send", json={"phone": PHONE})
    code = _stored_code(PHONE)
    tokens = client.post(
        f"{BASE}/auth/otp/verify", json={"phone": PHONE, "code": code}
    ).json()["data"]

    refreshed = client.post(
        f"{BASE}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["data"]["access_token"]
