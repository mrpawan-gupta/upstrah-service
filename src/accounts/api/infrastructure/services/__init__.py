"""Concrete infrastructure service adapters for the accounts app.

Realise application-layer ports with side-effecting implementations. In
this service OTP delivery is mocked, so the only adapter is a
console/logging dispatcher — no real SMS provider is contacted.

Services:
    MockOTPDispatcher — implements ``IOTPDispatcher`` via the console SMS stub
"""

from accounts.api.infrastructure.services.mock_otp_dispatcher import MockOTPDispatcher

__all__ = ["MockOTPDispatcher"]
