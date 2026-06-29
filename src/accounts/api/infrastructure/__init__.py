"""Infrastructure layer for the accounts app.

Adapters that realise the domain ports: Django-ORM ``repositories``, the
mocked OTP-delivery ``services``, and the ``di_container`` composition
root. Re-exports the module-level ``di_container`` singleton and the
FastAPI ``Depends()`` controller factories so endpoint modules import them
from one place.
"""

from accounts.api.infrastructure.di_container import (
    di_container,
    get_auth_controller,
    get_otp_controller,
    get_user_profile_controller,
)

__all__ = [
    "di_container",
    "get_auth_controller",
    "get_otp_controller",
    "get_user_profile_controller",
]
