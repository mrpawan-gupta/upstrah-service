from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.timestamp import TimeStampModel


class ConfigNamespace(models.TextChoices):
    COMPANY_WEBHOOK = "company_webhook", _("Company Webhook")
    COMPANY_KAFKA = "company_kafka", _("Company Kafka")
    COMPANY_RMQ = "company_rmq", _("Company RabbitMQ")
    COMPANY_SYNC = "company_sync", _("Company Sync")
    COMPANY_RETRY = "company_retry", _("Company Retry")


class ConfigDataType(models.TextChoices):
    STRING = "string", _("Text String")
    INTEGER = "integer", _("Integer Number")
    FLOAT = "float", _("Decimal Number")
    BOOLEAN = "boolean", _("True/False")
    JSON = "json", _("JSON Object")
    LIST = "list", _("JSON List")
    DATETIME = "datetime", _("Date and Time")
    DATE = "date", _("Date")
    TIME = "time", _("Time")


class KeyValueConfig(TimeStampModel):
    entity_type = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_("Entity Type"),
        help_text=_("Entity type (e.g., 'Company', 'Policy')"),
    )
    entity_id = models.PositiveIntegerField(
        db_index=True,
        verbose_name=_("Entity ID"),
        help_text=_("ID of the entity (e.g., company_id)"),
    )
    config_key = models.CharField(
        max_length=255,
        verbose_name=_("Config Key"),
        help_text=_("Configuration key (e.g., 'webhook_url', 'max_retries')"),
    )
    config_value = models.TextField(
        verbose_name=_("Config Value"),
        help_text=_("Configuration value (JSON-encoded if needed)"),
    )
    data_type = models.CharField(
        max_length=20,
        choices=ConfigDataType,
        default=ConfigDataType.STRING,
        verbose_name=_("Data Type"),
        help_text=_("Data type of the value"),
    )
    is_encrypted = models.BooleanField(
        default=False,
        verbose_name=_("Is Encrypted"),
        help_text=_("Whether value is encrypted (for secrets)"),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
        help_text=_("Whether configuration is active"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Human-readable description"),
    )
    tags = models.JSONField(
        default=list,
        verbose_name=_("Tags"),
        help_text=_("Tags for organizing configs (e.g., ['inbound', 'critical'])"),
    )

    class Meta:
        app_label = "common"
        verbose_name = _("Key-Value Configuration")
        verbose_name_plural = _("Key-Value Configurations")

    def __str__(self) -> str:
        return f"{self.entity_type}({self.entity_id})"


class ConfigHistory(TimeStampModel):
    """Audit trail row for a :class:`KeyValueConfig` mutation.
    Written alongside every config change so operators can reconstruct
    the prior value and actor — the live row itself only keeps the
    current value.
    """

    config = models.ForeignKey(
        KeyValueConfig,
        on_delete=models.CASCADE,
        verbose_name=_("Configuration"),
    )
    old_value = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Old Value"),
    )
    new_value = models.TextField(
        verbose_name=_("New Value"),
    )
    changed_by = models.CharField(
        max_length=255,
        verbose_name=_("Changed By"),
    )
    change_reason = models.TextField(
        blank=True,
        verbose_name=_("Change Reason"),
    )

    class Meta:
        app_label = "common"
        verbose_name = _("Configuration Change History")
        verbose_name_plural = _("Configuration Change Histories")
