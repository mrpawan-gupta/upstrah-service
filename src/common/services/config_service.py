"""Service for managing key-value configurations.

Provides both generic ConfigService for any entity type and specialized
CompanyConfigService for company-specific configurations.
"""

from typing import Any

from common.models import (
    ConfigHistory,
    ConfigNamespace,
    KeyValueConfig,
)


class ConfigService:
    """Service for accessing and managing configurations.

    Provides generic methods for get, set, delete, and list operations
    on configurations for any entity type.
    """

    @staticmethod
    def get_config(
        entity_type: str,
        entity_id: int,
        namespace: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get a single configuration value.

        Args:
            entity_type: Type of entity (e.g., 'Company')
            entity_id: ID of entity
            namespace: Configuration namespace
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default if not found
        """
        try:
            config = KeyValueConfig.objects.get(
                entity_type=entity_type,
                entity_id=entity_id,
                namespace=namespace,
                key=key,
                is_active=True,
            )
            return config.get_value()

        except KeyValueConfig.DoesNotExist:
            return default

    @staticmethod
    def set_config(
        entity_type: str,
        entity_id: int,
        namespace: str,
        key: str,
        value: Any,
        description: str = "",
        tags: list[str] | None = None,
        updated_by: str = "system",
    ) -> KeyValueConfig:
        """Set a configuration value.

        Creates or updates the configuration. Automatically handles type
        conversion and records change history.

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            namespace: Configuration namespace
            key: Configuration key
            value: Value to set
            description: Human-readable description
            tags: Tags for organizing configs
            updated_by: User or system making the change

        Returns:
            Created or updated KeyValueConfig instance
        """
        config, created = KeyValueConfig.objects.get_or_create(
            entity_type=entity_type,
            entity_id=entity_id,
            namespace=namespace,
            key=key,
            defaults={"description": description},
        )

        old_value = config.value
        config.set_value(value)
        config.description = description
        if tags:
            config.tags = tags
        config.updated_by = updated_by
        config.save()

        # Record in history
        if not created and old_value != config.value:
            ConfigHistory.objects.create(
                config=config,
                old_value=old_value,
                new_value=config.value,
                changed_by=updated_by,
            )

        return config

    @staticmethod
    def get_namespace_configs(
        entity_type: str,
        entity_id: int,
        namespace: str,
    ) -> dict[str, Any]:
        """Get all configurations in a namespace.

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            namespace: Configuration namespace

        Returns:
            Dictionary of {key: value} pairs
        """
        configs = KeyValueConfig.objects.filter(
            entity_type=entity_type,
            entity_id=entity_id,
            namespace=namespace,
            is_active=True,
        )

        return {config.key: config.get_value() for config in configs}

    @staticmethod
    def delete_config(
        entity_type: str,
        entity_id: int,
        namespace: str,
        key: str,
    ) -> bool:
        """Delete a configuration (soft delete - sets is_active=False).

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            namespace: Configuration namespace
            key: Configuration key

        Returns:
            True if deleted, False if not found
        """
        try:
            config = KeyValueConfig.objects.get(
                entity_type=entity_type,
                entity_id=entity_id,
                namespace=namespace,
                key=key,
            )
            config.is_active = False
            config.save()
            return True

        except KeyValueConfig.DoesNotExist:
            return False

    @staticmethod
    def get_by_tag(
        entity_type: str,
        entity_id: int,
        tag: str,
    ) -> list[KeyValueConfig]:
        """Get all configurations with a specific tag.

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            tag: Tag to search for

        Returns:
            List of matching KeyValueConfig instances
        """
        return KeyValueConfig.objects.filter(
            entity_type=entity_type,
            entity_id=entity_id,
            tags__contains=tag,
            is_active=True,
        )

    @staticmethod
    def get_history(
        entity_type: str,
        entity_id: int,
        namespace: str,
        key: str,
        limit: int = 50,
    ) -> list[ConfigHistory]:
        """Get change history for a configuration.

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            namespace: Configuration namespace
            key: Configuration key
            limit: Maximum number of history records to return

        Returns:
            List of ConfigHistory records (newest first)
        """
        try:
            config = KeyValueConfig.objects.get(
                entity_type=entity_type,
                entity_id=entity_id,
                namespace=namespace,
                key=key,
            )
            return config.confighistory_set.all()[:limit]

        except KeyValueConfig.DoesNotExist:
            return []


class CompanyConfigService:
    """Convenience service for company-specific configurations.

    Wraps ConfigService with company context for easier usage in company-related code.
    """

    def __init__(self, company_id: int):
        """Initialize with a company ID.

        Args:
            company_id: ID of the company
        """
        self.company_id = company_id
        self.entity_type = "Company"

    def get(
        self,
        namespace: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get a company configuration.

        Args:
            namespace: Configuration namespace
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        return ConfigService.get_config(
            entity_type=self.entity_type,
            entity_id=self.company_id,
            namespace=namespace,
            key=key,
            default=default,
        )

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        description: str = "",
        tags: list[str] | None = None,
    ) -> KeyValueConfig:
        """Set a company configuration.

        Args:
            namespace: Configuration namespace
            key: Configuration key
            value: Value to set
            description: Human-readable description
            tags: Tags for organizing configs

        Returns:
            Created or updated KeyValueConfig instance
        """
        return ConfigService.set_config(
            entity_type=self.entity_type,
            entity_id=self.company_id,
            namespace=namespace,
            key=key,
            value=value,
            description=description,
            tags=tags,
        )

    def get_namespace(self, namespace: str) -> dict[str, Any]:
        """Get all configurations in a namespace.

        Args:
            namespace: Configuration namespace

        Returns:
            Dictionary of {key: value} pairs
        """
        return ConfigService.get_namespace_configs(
            entity_type=self.entity_type,
            entity_id=self.company_id,
            namespace=namespace,
        )

    def get_webhook_config(self) -> dict[str, Any]:
        """Get webhook configuration for this company.

        Returns:
            Dictionary with webhook settings
        """
        return self.get_namespace(ConfigNamespace.COMPANY_WEBHOOK)

    def get_kafka_inbound_config(self) -> dict[str, Any]:
        """Get Kafka inbound configuration for this company.

        Returns:
            Dictionary with Kafka inbound settings
        """
        return self.get_namespace(ConfigNamespace.COMPANY_KAFKA)

    def get_rmq_inbound_config(self) -> dict[str, Any]:
        """Get RabbitMQ inbound configuration for this company.

        Returns:
            Dictionary with RabbitMQ inbound settings
        """
        return self.get_namespace(ConfigNamespace.COMPANY_RMQ)

    def get_sync_config(self) -> dict[str, Any]:
        """Get synchronization configuration for this company.

        Returns:
            Dictionary with sync settings
        """
        return self.get_namespace(ConfigNamespace.COMPANY_SYNC)

    def get_retry_config(self) -> dict[str, Any]:
        """Get retry configuration for this company.

        Returns:
            Dictionary with retry settings
        """
        return self.get_namespace(ConfigNamespace.COMPANY_RETRY)

    def is_webhook_enabled(self) -> bool:
        """Check if webhook is enabled for this company.

        Returns:
            True if webhook is enabled, False otherwise
        """
        return self.get(ConfigNamespace.COMPANY_WEBHOOK, "enabled", False)

    def get_webhook_url(self) -> str | None:
        """Get webhook URL for this company.

        Returns:
            Webhook URL or None if not configured
        """
        return self.get(ConfigNamespace.COMPANY_WEBHOOK, "url")

    def get_webhook_secret(self) -> str | None:
        """Get webhook secret for HMAC signing.

        Returns:
            Webhook secret or None if not configured
        """
        return self.get(ConfigNamespace.COMPANY_WEBHOOK, "secret")

    def is_kafka_inbound_enabled(self) -> bool:
        """Check if Kafka inbound is enabled for this company.

        Returns:
            True if Kafka inbound is enabled, False otherwise
        """
        return self.get(ConfigNamespace.COMPANY_KAFKA, "inbound_enabled", False)

    def is_rmq_inbound_enabled(self) -> bool:
        """Check if RabbitMQ inbound is enabled for this company.

        Returns:
            True if RabbitMQ inbound is enabled, False otherwise
        """
        return self.get(ConfigNamespace.COMPANY_RMQ, "inbound_enabled", False)

    def is_kafka_outbound_enabled(self) -> bool:
        """Check if Kafka outbound is enabled for this company.

        Returns:
            True if Kafka outbound is enabled, False otherwise
        """
        return self.get(ConfigNamespace.COMPANY_KAFKA, "outbound_enabled", False)

    def is_rmq_outbound_enabled(self) -> bool:
        """Check if RabbitMQ outbound is enabled for this company.

        Returns:
            True if RabbitMQ outbound is enabled, False otherwise
        """
        return self.get(ConfigNamespace.COMPANY_RMQ, "outbound_enabled", False)

    def get_kafka_outbound_config(self) -> dict[str, Any]:
        """Get Kafka outbound configuration for this company.

        Returns:
            Dictionary with Kafka outbound settings
        """
        return self.get_namespace(ConfigNamespace.COMPANY_KAFKA)

    def get_rmq_outbound_config(self) -> dict[str, Any]:
        """Get RabbitMQ outbound configuration for this company.

        Returns:
            Dictionary with RabbitMQ outbound settings
        """
        return self.get_namespace(ConfigNamespace.COMPANY_RMQ)

    def get_max_retries(self) -> int:
        """Get maximum retry count for this company.

        Returns:
            Maximum retry count (default: 3)
        """
        return self.get(ConfigNamespace.COMPANY_RETRY, "max_retries", 3)

    def get_retry_delay_seconds(self) -> int:
        """Get retry delay in seconds for this company.

        Returns:
            Retry delay in seconds (default: 60)
        """
        return self.get(ConfigNamespace.COMPANY_RETRY, "delay_seconds", 60)
