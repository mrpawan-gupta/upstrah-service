"""Custom django-allauth adapters for the Tolaram identity model.

Two adapter classes are registered via Django settings
(``ACCOUNT_ADAPTER`` and ``SOCIALACCOUNT_ADAPTER``):

* :class:`RudraAccountAdapter` — overrides allauth's default account
  adapter so we can control password-less user creation (partner-first
  users have no password on our side) and suppress allauth's own
  confirmation-email delivery (our event-driven pipeline in
  ``accounts/api/infrastructure/external_services/notifications`` owns
  that flow).
* :class:`RudraSocialAccountAdapter` — implements ``pre_social_login``
  so that when a Google/Apple login matches an existing verified user
  email on the Tolaram side, the incoming ``SocialLogin`` is linked to
  that user rather than creating a duplicate. This is the key hook that
  lets partner-synced users (who may have no password) seamlessly log
  into Tolaram directly once they claim their account.

Neither adapter holds state beyond what django-allauth itself tracks;
they're pure extension points.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

if TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin
    from django.http import HttpRequest

logger = structlog.get_logger(__name__)


class RudraAccountAdapter(DefaultAccountAdapter):
    """Tolaram-specific overrides for allauth's account adapter.

    Currently the adapter is a thin pass-through — it exists so that
    future overrides (custom password reset email template, custom
    username normalization, etc.) land in one obvious place. The
    subclass registration alone is enough to make allauth honour any
    hook we later add without having to touch settings.
    """

    def send_confirmation_mail(  # type: ignore[no-untyped-def]
        self, request, emailconfirmation, signup
    ) -> None:
        """Delegate email-confirmation delivery to our event pipeline.

        Rudra's notification system (``event_dispatcher`` +
        ``EmailProviderRouter``) owns all outbound email. We log the
        event so allauth's admin-side flows behave as expected but do
        NOT call ``super().send_confirmation_mail`` — that would send
        via allauth's default backend and bypass our provider router.

        Args:
            request: Incoming Django ``HttpRequest`` (may be ``None``).
            emailconfirmation: ``allauth.account.models.EmailConfirmation``.
            signup: ``True`` when the confirmation is for first signup.
        """
        logger.info(
            "email_confirmation_requested",
            user_id=getattr(emailconfirmation.email_address.user, "pk", None),
            email=emailconfirmation.email_address.email,
            key=emailconfirmation.key,
            is_signup=bool(signup),
        )
        # TODO(phase-3a-followup): publish an EmailConfirmationRequested
        # domain event once the rudra notification pipeline is extended
        # to understand allauth's confirmation keys. Until then operators
        # trigger re-sends through the existing forgot-password flow.


class RudraSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Link social logins to existing Tolaram users by verified email.

    When a Google or Apple sign-in produces a ``SocialLogin`` whose
    primary email matches an existing ``User`` (found via allauth's
    ``EmailAddress`` table) and that email is marked verified on our
    side, we attach the new ``SocialAccount`` to the existing user
    instead of letting allauth create a fresh account with a duplicated
    identity. This is the mirror image of the identifier-intersection
    matching used by the partner sync upsert in
    :mod:`accounts.api.application.use_cases.user_sync_use_cases`.
    """

    def pre_social_login(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> None:
        """Link ``sociallogin`` to an existing verified user when possible.

        Allauth calls this hook *before* it attempts to persist a new
        ``SocialAccount``; when ``sociallogin.user`` is set to an
        existing ``User``, allauth skips the create step and only
        attaches the ``SocialAccount``. That's exactly the shape we
        want for "same person, different sign-in provider".

        Args:
            request: Incoming Django request.
            sociallogin: Social login being processed by allauth.
        """
        # Already linked on a previous round-trip — nothing to do.
        if sociallogin.is_existing:
            return

        email = (sociallogin.user.email or "").strip().lower()
        if not email:
            return

        try:
            existing = EmailAddress.objects.select_related("user").get(
                email__iexact=email,
                verified=True,
            )
        except EmailAddress.DoesNotExist:
            return
        except EmailAddress.MultipleObjectsReturned:
            logger.info(
                "social_login_multiple_email_matches",
                provider=sociallogin.account.provider,
                email=email,
            )
            return

        sociallogin.connect(request, existing.user)
        logger.info(
            "social_login_linked_to_existing",
            provider=sociallogin.account.provider,
            user_id=existing.user.pk,
            email=email,
        )
