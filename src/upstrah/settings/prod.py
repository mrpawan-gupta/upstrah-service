"""Production settings.

Reads secrets and the database config from the environment. Set
DJANGO_SETTINGS_MODULE=upstrah.settings.prod and provide DJANGO_SECRET_KEY,
DJANGO_ALLOWED_HOSTS, and the POSTGRES_* variables.
"""
from __future__ import annotations

import os

from .base import *

DEBUG = False
ALLOWED_HOSTS = [
    h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "upstrah"),
        "USER": os.environ.get("POSTGRES_USER", "upstrah"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

# Security hardening (enabled behind TLS-terminating proxy).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
