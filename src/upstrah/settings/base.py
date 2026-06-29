"""Common Django settings shared by all environments.

Environment-specific modules (dev.py, prod.py) import from here and override.
Select one via DJANGO_SETTINGS_MODULE, e.g. ``upstrah.settings.dev``.
"""
from __future__ import annotations

import os
from pathlib import Path

# src/ — the import root that holds the `upstrah`, `apps`, and per-app packages.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "phonenumber_field",
    "accounts",
    "academies",
    "athletes",
    "teams",
    "training",
    "scouting",
    "feed",
    "chat",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "upstrah.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "upstrah.wsgi.application"
ASGI_APPLICATION = "upstrah.asgi.application"

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Phone numbers
# ---------------------------------------------------------------------------
PHONENUMBER_DEFAULT_REGION = os.environ.get("PHONENUMBER_DEFAULT_REGION", "US")
PHONENUMBER_DEFAULT_FORMAT = "E164"

# ---------------------------------------------------------------------------
# OTP (phone one-time-password login)
# ---------------------------------------------------------------------------
# Length of generated OTP codes; OTP_VALID_DURATION is read by the model and
# OTP_EXPIRE_SECONDS by the cache-backed handler — keep them in sync.
OTP_LENGTH = int(os.environ.get("OTP_LENGTH", "6"))
OTP_VALID_DURATION = int(os.environ.get("OTP_VALID_DURATION", "600"))
OTP_EXPIRE_SECONDS = OTP_VALID_DURATION
OTP_RATE_LIMIT_MAX = int(os.environ.get("OTP_RATE_LIMIT_MAX", "5"))
# Dev/QA overrides honoured by ``common.auth.otp.provider.OTPProvider`` —
# leave blank in production. SMS/OTP delivery is mocked in this service.
OTP_FIXED_CODE = os.environ.get("OTP_FIXED_CODE", "")
OTP_BYPASS_PHONE = os.environ.get("OTP_BYPASS_PHONE", "")
OTP_BYPASS_CODE = os.environ.get("OTP_BYPASS_CODE", "")
OTP_DELIVERY_CHANNEL = os.environ.get("OTP_DELIVERY_CHANNEL", "sms")

# ---------------------------------------------------------------------------
# JWT (RS256 access / refresh tokens)
# ---------------------------------------------------------------------------
# In real deployments JWT_PRIVATE_KEY / JWT_PUBLIC_KEY are PEM strings supplied
# via the environment. For local development and tests an ephemeral RSA keypair
# is generated at import time so the auth flow works out of the box.
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "RS256")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "upstrah-service")
JWT_EXPECTED_AUDIENCE = os.environ.get("JWT_EXPECTED_AUDIENCE", "tolaram")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.environ.get("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
)

JWT_PRIVATE_KEY = os.environ.get("JWT_PRIVATE_KEY", "")
JWT_PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "")

if not JWT_PRIVATE_KEY or not JWT_PUBLIC_KEY:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    _key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    JWT_PRIVATE_KEY = _key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    JWT_PUBLIC_KEY = (
        _key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )

# ---------------------------------------------------------------------------
# Cache (OTP codes, JWT blacklist, rate-limit counters)
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
