"""Application-layer ports (interfaces) for the accounts app.

Abstract collaborators the use cases depend on, kept here so a concrete
infrastructure adapter can be substituted via the DI container (and a fake
swapped in tests).

Ports:
    IOTPDispatcher — deliver an OTP code over a channel (mocked in this service)
"""

from accounts.api.application.interfaces.otp_dispatcher import IOTPDispatcher

__all__ = ["IOTPDispatcher"]
