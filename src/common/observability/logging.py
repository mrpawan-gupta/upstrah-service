"""Canonical Django ``LOGGING`` dict and ``structlog`` setup.

Shared across rudra-service, care-service, vms, kriya-service, and
angad-service. Edit in rudra first, then sync via ``cp -r`` per the
single-source-of-truth workflow.
"""

import structlog

LOG_VERBOSE_FORMAT = " ".join(
    [
        "%(asctime)s [%(levelname)s]",
        "%(name)s.%(funcName)s %(process)d",
        "%(thread)d %(message)s",
    ]
)
LOG_SIMPLE_FORMAT = "%(levelname)s %(message)s"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": LOG_VERBOSE_FORMAT,
        },
        "simple": {
            "format": LOG_SIMPLE_FORMAT,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "celery.beat": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "gunicorn": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "gunicorn.access": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "gunicorn.error": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "httpx": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "httpcore": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "urllib3": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "asyncio": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "multipart": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "redis": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "kombu": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "billiard": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "amqp": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}


def configure_structlog() -> None:
    """Install the canonical structlog processor chain.

    Called from every service's ``settings/base.py`` after Django's
    ``LOGGING`` is assigned, so Django, Celery and application loggers
    all emit JSON via the same pipeline.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(sort_keys=True),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
