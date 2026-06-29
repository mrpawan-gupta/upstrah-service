"""Abstract Django model mixin for contact fields.

Provides optional ``phone`` and ``email`` columns via :class:`ContactMixin`.
Include this mixin in any model that stores contact information; both fields
are optional so the mixin is usable on models that only need one channel.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


class ContactMixin(models.Model):
    """Abstract mixin adding optional ``phone`` and ``email`` columns.

    Both fields are ``blank=True`` so the mixin fits models that use
    only one channel. Phone values are normalised to E.164 per
    ``PHONENUMBER_DEFAULT_REGION`` / ``PHONENUMBER_DEFAULT_FORMAT`` —
    callers should not pre-format the value themselves.

    Attributes:
        phone: E.164 phone number; blank when only email is relevant.
        email: Contact email; blank when only phone is relevant.
    """

    phone = PhoneNumberField(blank=True, verbose_name=_("Phone"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))

    class Meta:
        abstract = True
