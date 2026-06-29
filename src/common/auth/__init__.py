"""Authentication and authorisation utilities for rudra-service.

Public surface
--------------
JWT:
    jwt_handler, JWTHandler  — sign / verify / blacklist
    TokenUser                — stateless request user backed by JWT claims

OTP:
    otp_handler, OTPHandler  — generate, verify, rate-limit
    OTPProvider              — low-level code generator

SSO:
    google_sso, GoogleSSO    — OAuth2 + id_token (web + mobile)
    apple_sso, AppleSSO      — Sign In with Apple (web + mobile)

Notifications:
    IEmailService, EmailMessage, ConsoleEmailService
    ISMSService, ConsoleSMSService

FastAPI dependencies:
    get_current_user         — validates bearer token, returns TokenUser
    get_company_ids          — resolves company PKs from X-Company-IDs header
    require_partner_or_user  — accepts user access tokens OR partner tokens
    require_scope            — dependency factory; rejects tokens missing a scope

RBAC guards:
    require_superuser, require_roles, require_permissions

Misc:
    password_reset_handler
"""

from common.auth.dependencies import get_company_ids, get_current_user
from common.auth.jwt.handler import JWTHandler, jwt_handler
from common.auth.jwt.token_user import TokenUser
from common.auth.notifications.email import (
    ConsoleEmailService,
    EmailMessage,
    IEmailService,
)
from common.auth.notifications.sms import ConsoleSMSService, ISMSService
from common.auth.otp.handler import OTPHandler, otp_handler
from common.auth.otp.provider import OTPProvider
from common.auth.password_reset_handler import password_reset_handler
from common.auth.permissions import (
    require_permissions,
    require_roles,
    require_superuser,
)
from common.auth.sso.apple import AppleSSO, apple_sso
from common.auth.sso.google import GoogleSSO, google_sso

__all__ = [
    "AppleSSO",
    "ConsoleEmailService",
    "ConsoleSMSService",
    "EmailMessage",
    "GoogleSSO",
    "IEmailService",
    "ISMSService",
    "JWTHandler",
    "OTPHandler",
    "OTPProvider",
    "TokenUser",
    "apple_sso",
    "get_company_ids",
    "get_current_user",
    "google_sso",
    "jwt_handler",
    "otp_handler",
    "password_reset_handler",
    "require_permissions",
    "require_roles",
    "require_superuser",
]
