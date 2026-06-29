"""Prometheus metrics collection for the CARE service.

Provides metrics for:
- HTTP request latency and status codes
- Celery task execution time and results
- Message broker operations (Kafka, RabbitMQ)
- Database queries
- Cache operations
- Event processing
"""

import time
from collections.abc import Callable
from functools import wraps

from prometheus_client import (  # noqa: F401  — re-exported for endpoints.py
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Create a registry for all metrics
REGISTRY = CollectorRegistry()

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
    registry=REGISTRY,
)

CELERY_TASK_TOTAL = Counter(
    "celery_task_total",
    "Total Celery tasks",
    ["task_name", "status"],
    registry=REGISTRY,
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    "celery_task_duration_seconds",
    "Celery task execution time",
    ["task_name"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=REGISTRY,
)

CELERY_TASK_RETRIES_TOTAL = Counter(
    "celery_task_retries_total",
    "Total Celery task retries",
    ["task_name", "reason"],
    registry=REGISTRY,
)

CELERY_QUEUE_SIZE = Gauge(
    "celery_queue_size",
    "Current size of Celery queue",
    ["queue_name"],
    registry=REGISTRY,
)

KAFKA_MESSAGES_PUBLISHED_TOTAL = Counter(
    "kafka_messages_published_total",
    "Total Kafka messages published",
    ["topic", "status"],
    registry=REGISTRY,
)

KAFKA_PUBLISH_LATENCY_SECONDS = Histogram(
    "kafka_publish_latency_seconds",
    "Kafka message publish latency",
    ["topic"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
    registry=REGISTRY,
)

KAFKA_MESSAGES_CONSUMED_TOTAL = Counter(
    "kafka_messages_consumed_total",
    "Total Kafka messages consumed",
    ["topic", "status"],
    registry=REGISTRY,
)

RMQ_MESSAGES_PUBLISHED_TOTAL = Counter(
    "rmq_messages_published_total",
    "Total RabbitMQ messages published",
    ["exchange", "routing_key", "status"],
    registry=REGISTRY,
)

RMQ_PUBLISH_LATENCY_SECONDS = Histogram(
    "rmq_publish_latency_seconds",
    "RabbitMQ message publish latency",
    ["exchange"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
    registry=REGISTRY,
)

RMQ_MESSAGES_CONSUMED_TOTAL = Counter(
    "rmq_messages_consumed_total",
    "Total RabbitMQ messages consumed",
    ["queue", "status"],
    registry=REGISTRY,
)

RMQ_CONNECTIONS_ACTIVE = Gauge(
    "rmq_connections_active",
    "Active RabbitMQ connections",
    registry=REGISTRY,
)

KAFKA_CONNECTIONS_ACTIVE = Gauge(
    "kafka_connections_active",
    "Active Kafka connections",
    registry=REGISTRY,
)

DOMAIN_EVENTS_PUBLISHED = Counter(
    "domain_events_published_total",
    "Total domain events published",
    ["event_type"],
    registry=REGISTRY,
)

EVENT_HANDLER_DURATION_SECONDS = Histogram(
    "event_handler_duration_seconds",
    "Event handler execution time",
    ["event_type", "handler"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
    registry=REGISTRY,
)

EVENT_HANDLER_ERRORS_TOTAL = Counter(
    "event_handler_errors_total",
    "Total event handler errors",
    ["event_type", "handler", "error_type"],
    registry=REGISTRY,
)

WEBHOOK_DELIVERIES_TOTAL = Counter(
    "webhook_deliveries_total",
    "Total webhook delivery attempts",
    ["status_code"],
    registry=REGISTRY,
)

WEBHOOK_DELIVERY_LATENCY_SECONDS = Histogram(
    "webhook_delivery_latency_seconds",
    "Webhook delivery latency",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
    registry=REGISTRY,
)

WEBHOOK_RETRIES_TOTAL = Counter(
    "webhook_retries_total",
    "Total webhook delivery retries",
    ["reason"],
    registry=REGISTRY,
)

WEBHOOK_DLQ_MESSAGES = Gauge(
    "webhook_dlq_messages_total",
    "Total messages in webhook DLQ",
    registry=REGISTRY,
)

DATABASE_QUERY_DURATION_SECONDS = Histogram(
    "database_query_duration_seconds",
    "Database query execution time",
    ["operation", "table"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
    registry=REGISTRY,
)

DATABASE_CONNECTIONS_ACTIVE = Gauge(
    "database_connections_active",
    "Active database connections",
    registry=REGISTRY,
)

CACHE_HITS_TOTAL = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"],
    registry=REGISTRY,
)

CACHE_MISSES_TOTAL = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"],
    registry=REGISTRY,
)

POLICIES_CREATED_TOTAL = Counter(
    "policies_created_total",
    "Total policies created",
    ["status"],
    registry=REGISTRY,
)

POLICIES_SUBMITTED_TOTAL = Counter(
    "policies_submitted_total",
    "Total policies submitted to CARE",
    registry=REGISTRY,
)

POLICY_CREATION_LATENCY_SECONDS = Histogram(
    "policy_creation_latency_seconds",
    "Policy creation end-to-end latency",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
    registry=REGISTRY,
)


def record_http_request(func: Callable) -> Callable:
    """Decorator to record HTTP request metrics.

    Usage in Django views:
        @record_http_request
        async def my_view(request):
            return Response(...)
    """

    @wraps(func)
    async def async_wrapper(request, *args, **kwargs):
        """Async variant: records HTTP metrics for coroutine-based views."""
        method = request.method
        endpoint = request.path
        start_time = time.time()

        try:
            response = await func(request, *args, **kwargs)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            duration = time.time() - start_time
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status=status,
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

        return response

    @wraps(func)
    def sync_wrapper(request, *args, **kwargs):
        """Sync variant: records HTTP metrics for synchronous views."""
        method = request.method
        endpoint = request.path
        start_time = time.time()

        try:
            response = func(request, *args, **kwargs)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            duration = time.time() - start_time
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status=status,
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

        return response

    # Return async or sync wrapper based on function
    if hasattr(func, "_is_coroutine"):
        return async_wrapper
    return sync_wrapper


def record_celery_task(task_name: str) -> Callable:
    """Decorator to record Celery task metrics.

    Usage in Celery task:
        @record_celery_task("my_task")
        def my_task():
            ...
    """

    def decorator(func: Callable) -> Callable:
        """Wrap the Celery task function with metrics instrumentation."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            """Execute the task and record duration, status, and retry counts."""
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                status = "success"
                return result
            except Exception as e:
                status = "failed"
                CELERY_TASK_RETRIES_TOTAL.labels(
                    task_name=task_name,
                    reason=type(e).__name__,
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                CELERY_TASK_TOTAL.labels(
                    task_name=task_name,
                    status=status,
                ).inc()
                CELERY_TASK_DURATION_SECONDS.labels(
                    task_name=task_name,
                ).observe(duration)

        return wrapper

    return decorator


def record_event_handler(event_type: str, handler_name: str) -> Callable:
    """Decorator to record event handler metrics.

    Usage in event handler:
        @record_event_handler("PolicyCreatedSuccessfullyEvent", "handle_webhook")
        async def handle_policy_created(event):
            ...
    """

    def decorator(func: Callable) -> Callable:
        """Wrap the event handler function with metrics instrumentation."""

        @wraps(func)
        async def async_wrapper(event):
            """Async variant: records event handler duration and error counts."""
            start_time = time.time()
            try:
                result = await func(event)
                return result
            except Exception as e:
                EVENT_HANDLER_ERRORS_TOTAL.labels(
                    event_type=event_type,
                    handler=handler_name,
                    error_type=type(e).__name__,
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                EVENT_HANDLER_DURATION_SECONDS.labels(
                    event_type=event_type,
                    handler=handler_name,
                ).observe(duration)

        @wraps(func)
        def sync_wrapper(event):
            """Sync variant: records event handler duration and error counts."""
            start_time = time.time()
            try:
                result = func(event)
                return result
            except Exception as e:
                EVENT_HANDLER_ERRORS_TOTAL.labels(
                    event_type=event_type,
                    handler=handler_name,
                    error_type=type(e).__name__,
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                EVENT_HANDLER_DURATION_SECONDS.labels(
                    event_type=event_type,
                    handler=handler_name,
                ).observe(duration)

        # Return async or sync wrapper
        if hasattr(func, "_is_coroutine"):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_metrics_text() -> bytes:
    """Get all metrics in Prometheus text format.

    Usage in Django view:
        from django.http import HttpResponse

        def metrics_view(request):
            return HttpResponse(
                get_metrics_text(),
                content_type=CONTENT_TYPE_LATEST
            )
    """
    return generate_latest(REGISTRY)


def update_connection_metrics(service_type: str, count: int) -> None:
    """Update active connection count for a service.

    Args:
        service_type: "kafka", "rmq", or "database"
        count: Current connection count
    """
    if service_type == "kafka":
        KAFKA_CONNECTIONS_ACTIVE.set(count)
    elif service_type == "rmq":
        RMQ_CONNECTIONS_ACTIVE.set(count)
    elif service_type == "database":
        DATABASE_CONNECTIONS_ACTIVE.set(count)


def update_dlq_metrics(dlq_type: str, count: int) -> None:
    """Update dead letter queue metrics.

    Args:
        dlq_type: Type of DLQ ("webhook", "kafka", "rmq")
        count: Current message count in DLQ
    """
    if dlq_type == "webhook":
        WEBHOOK_DLQ_MESSAGES.set(count)
