"""Email and SMS service interfaces and development stubs."""

from common.auth.notifications.email import (
    ConsoleEmailService,
    EmailMessage,
    IEmailService,
    console_email_service,
)
from common.auth.notifications.sms import (
    ConsoleSMSService,
    ISMSService,
    console_sms_service,
)

__all__ = [
    "ConsoleEmailService",
    "ConsoleSMSService",
    "EmailMessage",
    "IEmailService",
    "ISMSService",
    "console_email_service",
    "console_sms_service",
]
