"""Use-case unit tests for ``AuthUseCases`` with fake repositories.

Exercises the OTP send + verify flow against in-memory fakes (no DB, no
real SMS), asserting the business rules: send returns the TTL and
dispatches once; verify rejects a bad code and consumes the row + mints a
token pair on success.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from accounts.api.application.dtos.auth_dtos import OTPSendDTO, OTPVerifyDTO
from accounts.api.application.interfaces.otp_dispatcher import IOTPDispatcher
from accounts.api.application.use_cases.auth_use_cases import AuthUseCases
from common.auth.otp.handler import otp_handler
from common.exceptions.exceptions import AuthenticationError

PHONE = "+15550001111"


class _FakeOTPRow:
    """In-memory OTP row supporting the methods the use case calls."""

    def __init__(self, phone: str) -> None:
        self.phone = phone
        self.otp = "0000"
        self.expires_at = datetime.now(UTC) + timedelta(seconds=600)

    def set_otp_and_validity(self) -> None:
        self.otp = "4321"
        self.expires_at = datetime.now(UTC) + timedelta(seconds=600)

    def is_valid(self) -> bool:
        return datetime.now(UTC) <= self.expires_at


class _FakeOTPRepo:
    """Fake ``IOTPRepository`` keeping OTP rows in a dict."""

    def __init__(self) -> None:
        self.rows: dict[str, _FakeOTPRow] = {}
        self.deleted: list[str] = []

    async def get_or_create(self, phone: str):
        if phone in self.rows:
            return self.rows[phone], False
        row = _FakeOTPRow(phone)
        row.set_otp_and_validity()
        self.rows[phone] = row
        return row, True

    async def save(self, otp_obj) -> None:
        self.rows[otp_obj.phone] = otp_obj

    async def get_by_phone(self, phone: str):
        return self.rows.get(phone)

    async def delete_row(self, otp_obj) -> None:
        self.deleted.append(otp_obj.phone)
        self.rows.pop(otp_obj.phone, None)


class _FakeUser:
    pk = 7


class _FakeAuthRepo:
    """Fake ``IAuthRepository`` returning a static user + empty claims."""

    async def get_or_create_user_by_phone(self, phone: str):
        return _FakeUser(), True

    async def get_user_by_id(self, user_id):
        return _FakeUser()

    async def get_user_token_claims(self, user_id):
        return {"is_superuser": False, "is_staff": False, "roles": [], "scopes": []}


class _FakeDispatcher(IOTPDispatcher):
    """Fake OTP dispatcher recording each delivery."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def send_otp(self, *, phone: str, otp_code: str, channel: str) -> None:
        self.calls.append({"phone": phone, "otp_code": otp_code, "channel": channel})


@pytest.fixture(autouse=True)
def _clear_otp_cache():
    """Reset the cache-backed OTP rate/verify counters between tests."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.mark.asyncio
async def test_send_otp_returns_ttl_and_dispatches_once() -> None:
    """``send_otp`` returns the configured TTL and dispatches exactly once."""
    dispatcher = _FakeDispatcher()
    uc = AuthUseCases(_FakeAuthRepo(), _FakeOTPRepo(), dispatcher)

    ttl = await uc.send_otp(OTPSendDTO(phone=PHONE))

    assert ttl == 600
    assert len(dispatcher.calls) == 1
    assert dispatcher.calls[0]["phone"] == PHONE


@pytest.mark.asyncio
async def test_verify_otp_rejects_bad_code() -> None:
    """A wrong code raises ``AuthenticationError`` and does not consume the row."""
    otp_repo = _FakeOTPRepo()
    uc = AuthUseCases(_FakeAuthRepo(), otp_repo, _FakeDispatcher())
    await uc.send_otp(OTPSendDTO(phone=PHONE))

    with pytest.raises(AuthenticationError):
        await uc.verify_otp(OTPVerifyDTO(phone=PHONE, code="9999"))
    assert PHONE not in otp_repo.deleted


@pytest.mark.asyncio
async def test_verify_otp_success_consumes_row_and_mints_tokens() -> None:
    """A correct code consumes the OTP row and returns a token pair entity."""
    otp_repo = _FakeOTPRepo()
    uc = AuthUseCases(_FakeAuthRepo(), otp_repo, _FakeDispatcher())
    await uc.send_otp(OTPSendDTO(phone=PHONE))
    code = otp_repo.rows[PHONE].otp
    otp_handler.clear_verify_attempts(PHONE)

    tokens = await uc.verify_otp(OTPVerifyDTO(phone=PHONE, code=code))

    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.token_type == "bearer"
    assert PHONE in otp_repo.deleted
