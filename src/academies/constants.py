"""Enumerations and constant choices for the academies app.

Centralises the ``TextChoices`` constants referenced by the ``academies``
models and the clean-architecture ``api/`` tree so the ORM layer and the
domain layer share one source of truth.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class AcademyStatus(models.TextChoices):
    """Lifecycle status of an :class:`academies.models.Academy`."""

    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")


class RegistrationType(models.TextChoices):
    """Legal registration type of an :class:`academies.models.Academy`."""

    PROPRIETORSHIP = "proprietorship", _("Proprietorship")
    PARTNERSHIP = "partnership", _("Partnership")
    PRIVATE_LIMITED = "private_limited", _("Private Limited")
    TRUST = "trust", _("Trust")
    SOCIETY = "society", _("Society")
    OTHER = "other", _("Other")


class MembershipRole(models.TextChoices):
    """Role a member holds within an academy."""

    ATHLETE = "athlete", _("Athlete")
    COACH = "coach", _("Coach")
    ACADEMY_ADMIN = "academy_admin", _("Academy Admin")
    ACADEMY_HEAD = "academy_head", _("Academy Head")
    ACADEMY_STAFF = "academy_staff", _("Academy Staff")
    SPECTATOR = "spectator", _("Spectator / Enthusiast")
    PARENT_GUARDIAN = "parent_guardian", _("Parent / Guardian")
    SCOUT_RECRUITER = "scout_recruiter", _("Scout / Recruiter")


class MembershipStatus(models.TextChoices):
    """Approval status of a membership application (apply → review)."""

    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
