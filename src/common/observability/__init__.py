"""Observability package — logging, metrics, health checks, and Celery signals."""

from common.observability.celery_signals import register_celery_signals
from common.observability.health import HealthCheckService
from common.observability.logging import LOGGING, configure_structlog
from common.observability.metrics import (
    CELERY_TASK_DURATION_SECONDS,
    CELERY_TASK_TOTAL,
    DOMAIN_EVENTS_PUBLISHED,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    KAFKA_MESSAGES_PUBLISHED_TOTAL,
    KAFKA_PUBLISH_LATENCY_SECONDS,
    REGISTRY,
    RMQ_MESSAGES_PUBLISHED_TOTAL,
    RMQ_PUBLISH_LATENCY_SECONDS,
    WEBHOOK_DELIVERIES_TOTAL,
    WEBHOOK_DELIVERY_LATENCY_SECONDS,
    get_metrics_text,
    record_celery_task,
    record_event_handler,
    record_http_request,
    update_connection_metrics,
    update_dlq_metrics,
)

__all__ = [
    # Logging
    "LOGGING",
    "configure_structlog",
    # Celery signals
    "register_celery_signals",
    # Metrics
    "REGISTRY",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "CELERY_TASK_TOTAL",
    "CELERY_TASK_DURATION_SECONDS",
    "KAFKA_MESSAGES_PUBLISHED_TOTAL",
    "KAFKA_PUBLISH_LATENCY_SECONDS",
    "RMQ_MESSAGES_PUBLISHED_TOTAL",
    "RMQ_PUBLISH_LATENCY_SECONDS",
    "DOMAIN_EVENTS_PUBLISHED",
    "WEBHOOK_DELIVERIES_TOTAL",
    "WEBHOOK_DELIVERY_LATENCY_SECONDS",
    "record_http_request",
    "record_celery_task",
    "record_event_handler",
    "get_metrics_text",
    "update_connection_metrics",
    "update_dlq_metrics",
    # Health
    "HealthCheckService",
]
