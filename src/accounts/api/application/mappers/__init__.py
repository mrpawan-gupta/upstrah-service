"""Mappers for the accounts application layer.

Static-method classes that convert between Pydantic schemas, DTOs, domain
entities, and ORM rows. The mapper is the only serialization boundary —
``model_dump()`` appears here and nowhere else, and ``orm_to_entity``
never leaks an ORM object upward.

Mappers:
    AuthMapper        — auth token entity ↔ DTO ↔ response
    OTPMapper         — OTP ORM ↔ entity ↔ DTO ↔ response
    UserProfileMapper — UserProfile ORM ↔ entity ↔ DTO ↔ response
"""

from accounts.api.application.mappers.auth_mapper import AuthMapper
from accounts.api.application.mappers.otp_mapper import OTPMapper
from accounts.api.application.mappers.user_profile_mapper import UserProfileMapper

__all__ = [
    "AuthMapper",
    "OTPMapper",
    "UserProfileMapper",
]
