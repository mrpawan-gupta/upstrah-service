"""Enumerations and constant choices for the accounts app.

Centralises the ``TextChoices`` / ``StrEnum`` constants referenced by the
``accounts`` models and the clean-architecture ``api/`` tree so that both
the ORM layer and the domain layer share one source of truth.
"""

from __future__ import annotations

from enum import StrEnum

from django.db import models
from django.utils.translation import gettext_lazy as _


class Sex(models.TextChoices):
    """Biological-sex choices stored as a single-character code on ``UserProfile``."""

    MALE = "m", _("Male")
    FEMALE = "f", _("Female")
    OTHER = "o", _("Other")


class Role(models.TextChoices):
    """Top-level onboarding role assigned to a user during sign-up."""

    CUSTOMER = "customer", _("Customer")
    AGENT = "agent", _("Agent")
    PARTNER = "partner", _("Partner")


class SubRole(models.TextChoices):
    """Finer-grained role qualifier captured alongside :class:`Role`."""

    INDIVIDUAL = "individual", _("Individual")
    BUSINESS = "business", _("Business")
    BROKER = "broker", _("Broker")


class OtpChannel(StrEnum):
    """Delivery channels an OTP can be dispatched over."""

    SMS = "sms"
    WHATSAPP = "whatsapp"
    AUTO = "auto"


class TokenType(StrEnum):
    """JWT ``token_type`` claim values minted by the auth flow."""

    ACCESS = "access"
    REFRESH = "refresh"
    SERVICE = "service"
    PARTNER = "partner"
