"""Django ORM models for the academies app.

Defines :class:`Academy` (a sports academy owned by a creating user) and
:class:`Membership` (a user's application to an academy, transitioning
``pending → approved/rejected``). Both extend
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

from academies.constants import AcademyStatus, MembershipRole, MembershipStatus
from common.models import TimeStampModel


class Academy(TimeStampModel):
    """A sports academy owned by the user that created it.

    Attributes:
        name:        Display name of the academy.
        sport:       Primary sport the academy trains.
        description: Optional free-text description.
        city:        Optional city the academy operates in.
        status:      ``active`` (default) or ``inactive``.
        created_by:  Owning :class:`accounts.User`; protected from delete
            so an academy is never orphaned.
    """

    name = models.CharField(max_length=255, verbose_name=_("Name"))
    sport = models.CharField(max_length=100, verbose_name=_("Sport"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    city = models.CharField(max_length=120, blank=True, verbose_name=_("City"))
    status = models.CharField(
        max_length=16,
        choices=AcademyStatus.choices,
        default=AcademyStatus.ACTIVE,
        verbose_name=_("Status"),
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
