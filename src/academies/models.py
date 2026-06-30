"""Django ORM models for the academies app.

Defines :class:`Sport` (a trainable discipline), :class:`Academy` (a sports
academy owned by a creating user, training one or more :class:`Sport` via a
M2M) and :class:`Membership` (a user's application to an academy,
transitioning ``pending → approved/rejected``). All extend
:class:`common.models.TimeStampModel` for ``created_at`` / ``updated_at``
and lifecycle hooks. Foreign keys to ``AUTH_USER_MODEL`` are local
in-service references (the no-cross-service-FK rule applies to *other*
services). No ``FileField`` and no lifecycle ``*_at`` business columns beyond
the base mixin's audit stamps, per the storage rules.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from academies.constants import (
    AcademyStatus,
    MembershipRole,
    MembershipStatus,
    RegistrationType,
)
from common.models import TimeStampModel


class Sport(TimeStampModel):
    """A trainable sport/discipline an academy can offer.

    Attributes:
        name:      Unique display name of the sport.
        is_active: Whether the sport is selectable (default ``True``).
    """

    name = models.CharField(max_length=100, unique=True, verbose_name=_("Name"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name = _("Sport")
        verbose_name_plural = _("Sports")

    def __str__(self) -> str:
        return self.name


class Academy(TimeStampModel):
    """A sports academy owned by the user that created it.

    Attributes:
        name:                  Display name of the academy.
        sports:                The :class:`Sport` disciplines trained (M2M).
        description:           Optional free-text description.
        city:                  Optional city the academy operates in.
        status:                ``active`` (default) or ``inactive``.
        legal_name:            Registered legal entity name.
        address:              Full postal address.
        email:                 Contact email.
        phone:                 Contact phone (E.164).
        registration_type:     Legal registration type.
        gst_number:            GST registration number.
        website:               Public website URL.
        social_links:          Map of ``{platform: url}``.
        athlete_count:         Self-reported number of athletes.
        coach_count:           Self-reported number of coaches.
        primary_contact_name:  Primary contact person's name.
        primary_contact_phone: Primary contact person's phone (E.164).
        created_by:            Owning :class:`accounts.User`; protected from
            delete so an academy is never orphaned.
    """

    name = models.CharField(max_length=255, verbose_name=_("Name"))
    sports = models.ManyToManyField(
        Sport,
        related_name="academies",
        blank=True,
        verbose_name=_("Sports"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    city = models.CharField(max_length=120, blank=True, verbose_name=_("City"))
    status = models.CharField(
        max_length=16,
        choices=AcademyStatus.choices,
        default=AcademyStatus.ACTIVE,
        verbose_name=_("Status"),
    )
    legal_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("Legal Name")
    )
    address = models.TextField(blank=True, verbose_name=_("Address"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    phone = PhoneNumberField(blank=True, verbose_name=_("Phone"))
    registration_type = models.CharField(
        max_length=32,
        choices=RegistrationType.choices,
        blank=True,
        verbose_name=_("Registration Type"),
    )
    gst_number = models.CharField(
        max_length=20, blank=True, verbose_name=_("GST Number")
    )
    website = models.URLField(blank=True, verbose_name=_("Website"))
    social_links = models.JSONField(
        default=dict, blank=True, verbose_name=_("Social Links")
    )
    athlete_count = models.PositiveIntegerField(
        default=0, verbose_name=_("Athlete Count")
    )
    coach_count = models.PositiveIntegerField(
        default=0, verbose_name=_("Coach Count")
    )
    primary_contact_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("Primary Contact Name")
    )
    primary_contact_phone = PhoneNumberField(
        blank=True, verbose_name=_("Primary Contact Phone")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="academies_created",
        verbose_name=_("Created By"),
    )

    class Meta:
        verbose_name = _("Academy")
        verbose_name_plural = _("Academies")

    def __str__(self) -> str:
        return self.name


class Membership(TimeStampModel):
    """A user's membership application to an academy.

    Powers the apply → pending → approved/rejected flow. A user may hold at
    most one membership per academy (``unique_together``).

    Attributes:
        user:     The applying :class:`accounts.User`.
        academy:  The :class:`Academy` applied to.
        role:     Requested role (head/coach/admin/staff/athlete).
        status:   ``pending`` (default), ``approved``, or ``rejected``.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("User"),
    )
    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("Academy"),
    )
    role = models.CharField(
        max_length=16,
        choices=MembershipRole.choices,
        verbose_name=_("Role"),
    )
    status = models.CharField(
        max_length=16,
        choices=MembershipStatus.choices,
        default=MembershipStatus.PENDING,
        verbose_name=_("Status"),
    )

    class Meta:
        verbose_name = _("Membership")
        verbose_name_plural = _("Memberships")
        unique_together = ("user", "academy")

    def __str__(self) -> str:
        return f"membership({self.user_id}@{self.academy_id})"
