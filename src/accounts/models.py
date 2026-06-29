
import datetime

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_lifecycle import AFTER_CREATE, hook
from phonenumber_field.modelfields import PhoneNumberField

from accounts.constants import Role, Sex, SubRole
from common.auth.otp.provider import OTPProvider
from common.models import TimeStampModel
from common.utils import generate_snowflake


class UserManager(DjangoUserManager):
    """Extends Django's UserManager to auto-generate a Snowflake username."""

    use_in_migrations = True

    def create_user(self, username=None, email=None, password=None, **extra_fields):
        if not username:
            username = str(generate_snowflake())
        return super().create_user(
            username, email=email, password=password, **extra_fields
        )

    def create_superuser(
        self, username=None, email=None, password=None, **extra_fields
    ):
        if not username:
            username = str(generate_snowflake())
        return super().create_superuser(
            username, email=email, password=password, **extra_fields
        )


class User(TimeStampModel, AbstractUser):
    """Platform user — lean auth identity row.

    ``username`` is auto-filled with a Snowflake so that partner-first
    phone-OTP flows (where ``email`` is blank) cannot collide on a plain
    unique constraint. Authoritative email uniqueness lives on
    ``allauth.account.models.EmailAddress`` — do **not** assume
    ``User.email`` is unique.

    Demographics (``sex``, ``dob``) and notification preferences live on
    :class:`UserProfile` (1:1, ``user.profile``) so this row stays
    focused on authentication concerns.

    Attributes:
        phone: Optional E.164 phone; use :class:`PhoneNumber` for
            verified/primary tracking — this field is a convenience copy.
    """

    phone = PhoneNumberField(blank=True, verbose_name=_("Phone"))

    objects = UserManager()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def save(self, *args, **kwargs):
        """Assign a Snowflake username when ``id`` and ``username`` are both unset.

        The dual guard exists so an explicitly-seeded username (migrations,
        fixtures, manual admin creates) is never overwritten. Note that
        the ``id`` column itself is still Django's default auto-increment;
        only ``username`` carries the Snowflake value. Full per-row
        Snowflake PKs are tracked separately.
        """
        if not self.pk and not self.username:
            self.username = generate_snowflake()
        return super().save(*args, **kwargs)

    @hook(AFTER_CREATE)
    def _create_profile(self):
        UserProfile.objects.get_or_create(user=self)

    def __str__(self):
        return str(self.username)


class UserProfile(TimeStampModel):
    """Per-user demographics and notification preferences (1:1 with :class:`User`).

    Split off :class:`User` so the auth row stays minimal and future
    profile fields (address, KYC, locale, avatar) can land here without
    touching ``User``. Access via ``user.profile``; the row is created
    lazily — callers should use
    ``UserProfile.objects.get_or_create(user=user)`` rather than assume
    existence.

    Attributes:
        user: Owning :class:`User`. Cascade-deletes with the user.
        sex: Single-char code (``m``/``f``/``o``), nullable.
        dob: Date of birth, nullable.
        is_whatsapp_notification_enabled: Per-user opt-in for WhatsApp.
        is_email_notification_enabled: Per-user opt-in for email.
        is_phone_notification_enabled: Per-user opt-in for SMS/call.
        role: Top-level onboarding role (customer/agent/partner), nullable
            until the user completes onboarding.
        sub_role: Finer-grained role qualifier, nullable.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("User"),
    )
    sex = models.CharField(
        max_length=1,
        choices=Sex.choices,
        null=True,
        blank=True,
        verbose_name=_("Sex"),
    )
    dob = models.DateField(null=True, blank=True, verbose_name=_("Date of Birth"))
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        null=True,
        blank=True,
        verbose_name=_("Role"),
    )
    sub_role = models.CharField(
        max_length=16,
        choices=SubRole.choices,
        null=True,
        blank=True,
        verbose_name=_("Sub Role"),
    )
    is_whatsapp_notification_enabled = models.BooleanField(
        default=True, verbose_name=_("WhatsApp Notifications")
    )
    is_email_notification_enabled = models.BooleanField(
        default=True, verbose_name=_("Email Notifications")
    )
    is_phone_notification_enabled = models.BooleanField(
        default=True, verbose_name=_("Phone Notifications")
    )

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self) -> str:
        return f"profile({self.user.username})"


class OTP(TimeStampModel):
    """One-time code keyed by phone **or** email.

    On first save (when ``otp`` and ``expires_at`` are blank) the model
    auto-generates a random numeric code via :meth:`set_otp_and_validity`.
    A QA bypass is available when both ``OTP_BYPASS_PHONE`` and
    ``OTP_BYPASS_CODE`` are set: if the row's phone matches the
    configured bypass phone, the configured bypass code is issued
    instead of a random one. Production must leave both settings blank
    to disable the bypass.

    Attributes:
        otp: Generated numeric code (≤ 6 chars).
        phone: E.164 phone the code was sent to; unique and nullable so
            an email-only row can coexist.
        email: Email the code was sent to; unique and nullable for the
            symmetric reason.
        expires_at: Expiry stamp; :meth:`is_valid` compares against
            ``timezone.now()``.
    """

    otp = models.CharField(max_length=6, null=True, verbose_name=_("OTP code"))
    phone = PhoneNumberField(
        unique=True, null=True, blank=True, verbose_name=_("Phone")
    )
    email = models.EmailField(
        max_length=150, unique=True, null=True, blank=True, verbose_name=_("Email")
    )
    expires_at = models.DateTimeField(
        verbose_name=_("Valid Until"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("OTP")
        verbose_name_plural = _("OTPs")

    def __str__(self):
        return f"OTP({self.pk})"

    def save(self, *args, **kwargs):
        """Auto-generate OTP and validity when either field is missing.

        Either-missing (not both-missing) so a caller who sets ``otp``
        manually but forgets ``expires_at`` does not produce a row that
        crashes :meth:`is_valid`.
        """
        if not self.otp or not self.expires_at:
            self.set_otp_and_validity()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate that at least one of ``phone`` or ``email`` is provided."""
        super().clean()
        if self.phone is None and self.email is None:
            raise ValidationError(_("Either phone or email must be provided."))

    def set_otp_and_validity(self):
        """Generate an OTP code and set the expiry timestamp."""
        self.otp = OTPProvider().generate(
            length=settings.OTP_LENGTH, phone=str(self.phone)
        )
        self.expires_at = timezone.now() + datetime.timedelta(
            seconds=settings.OTP_VALID_DURATION
        )

    def reset(self):
        """Re-generate the OTP code and expiry, then persist."""
        self.set_otp_and_validity()
        self.save()

    def is_valid(self):
        """Return ``True`` if the OTP has not yet expired.

        Returns ``False`` when ``expires_at`` has not been set — a row
        with a null expiry is treated as invalid rather than crashing
        the comparison.
        """
        if self.expires_at is None:
            return False
        return timezone.now() <= self.expires_at


class PhoneNumber(TimeStampModel):
    """Verified phone records per user.

    Phone OTP login uses the row with ``primary=True`` to pick the
    canonical entry when a user has multiple numbers. The uniqueness of
    ``phone`` at the table level blocks the same number from being
    registered twice across different users.

    Attributes:
        user: Owning :class:`User`.
        phone: E.164 number; table-wide unique.
        verified: Set after an OTP challenge succeeds for this number.
        primary: Marks the canonical login number. At most one row per
            user may be primary (enforced by a partial unique DB
            constraint added in migrations).
    """

    user = models.ForeignKey(
        User,
        verbose_name=_("User"),
        on_delete=models.CASCADE,
        related_name="phone_numbers",
    )
    phone = PhoneNumberField(unique=True, verbose_name=_("Phone"))
    verified = models.BooleanField(verbose_name=_("Verified"), default=False)
    primary = models.BooleanField(
        default=False,
        verbose_name=_("Primary"),
        help_text=_(
            "At most one phone per user can be the primary; enforced via "
            "a partial unique constraint on (user) where primary=True."
        ),
    )

    class Meta:
        verbose_name = _("Phone Number")
        verbose_name_plural = _("Phone Numbers")
        constraints = [
            # Partial-unique: at most one primary phone per user.
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(primary=True),
                name="uniq_primary_phone_per_user",
            ),
        ]

    def __str__(self):
        return str(self.phone)
