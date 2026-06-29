"""Local / test settings.

Used by the test suite (``pytest.ini`` sets
``DJANGO_SETTINGS_MODULE=upstrah.settings.local``) and for local development.
Mirrors :mod:`upstrah.settings.dev`: SQLite database, ``DEBUG`` on, and a
fixed OTP code so the phone-OTP login flow is deterministic in tests.
"""
from __future__ import annotations

from .base import *
from .base import BASE_DIR

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
