"""FastAPI integration test for the academies endpoints.

Drives the real ASGI surface via ``TestClient`` against a real DB
transaction (``@pytest.mark.django_db(transaction=True)``). Reuses the
phone → OTP → JWT flow (as in ``test_auth_flow``) to obtain an access
token, then creates an academy and lists it, and exercises the membership
apply → approve transition.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from upstrah.asgi import get_application

PHONE = "+15049684139"
ACCOUNTS = "/accounts/api/v1"
ACADEMIES = "/academies/api/v1"


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


def _auth_headers(client: TestClient) -> dict[str, str]:
    """Run the OTP flow and return an Authorization header for the new user."""
    from accounts.models import OTP

    client.post(f"{ACCOUNTS}/auth/otp/send", json={"phone": PHONE})
    code = OTP.objects.get(phone=PHONE).otp
    tokens = client.post(
        f"{ACCOUNTS}/auth/otp/verify", json={"phone": PHONE, "code": code}
    ).json()["data"]
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.django_db(transaction=True)
def test_create_then_list_academy(client: TestClient) -> None:
    """A created academy appears in the paginated list."""
    headers = _auth_headers(client)

    created = client.post(
        f"{ACADEMIES}/academies",
        json={"name": "Riverside FC", "sport": "Football", "city": "Lagos"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()["data"]
    assert body["name"] == "Riverside FC"
    assert body["status"] == "active"
    academy_id = body["id"]

    listed = client.get(f"{ACADEMIES}/academies", headers=headers)
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    ids = [a["id"] for a in payload["data"]]
    assert academy_id in ids
    assert payload["meta"]["total"] >= 1


@pytest.mark.django_db(transaction=True)
def test_membership_apply_then_approve(client: TestClient) -> None:
    """Apply creates a pending membership; approve transitions it."""
    headers = _auth_headers(client)

    academy_id = client.post(
        f"{ACADEMIES}/academies",
        json={"name": "Court Kings", "sport": "Basketball"},
        headers=headers,
    ).json()["data"]["id"]

    applied = client.post(
        f"{ACADEMIES}/academies/{academy_id}/memberships",
        json={"role": "athlete"},
        headers=headers,
    )
    assert applied.status_code == 201, applied.text
    membership = applied.json()["data"]
    assert membership["status"] == "pending"

    approved = client.post(
        f"{ACADEMIES}/memberships/{membership['id']}/approve", headers=headers
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["status"] == "approved"


@pytest.mark.django_db(transaction=True)
def test_academy_requires_auth(client: TestClient) -> None:
    """Listing academies without a token is rejected."""
    resp = client.get(f"{ACADEMIES}/academies")
    assert resp.status_code == 401, resp.text
