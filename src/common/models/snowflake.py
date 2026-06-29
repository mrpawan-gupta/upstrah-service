"""Abstract mixin that adds a Snowflake ID field to any Django model."""

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.utils import generate_snowflake


class SnowflakeMixin(models.Model):
    """Abstract mixin that adds an auto-generated ``snowflake`` field.

    The field is a ``BigIntegerField`` with ``db_index=True`` and
    ``default=generate_snowflake``, so every new row gets a unique,
    time-ordered Snowflake ID without any extra ``save()`` override.

    This is not a primary key — the row's ``id`` (``BigAutoField``) remains
    the PK.  Use ``snowflake`` as the external-facing identifier in URLs and
    API responses.

    Usage::

        class MyModel(SnowflakeMixin, TimeStampModel):
            ...
    """

    snowflake = models.BigIntegerField(
        db_index=True,
        default=generate_snowflake,
        verbose_name=_("Snowflake"),
    )

    class Meta:
        abstract = True
