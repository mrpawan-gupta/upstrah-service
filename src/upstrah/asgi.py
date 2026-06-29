"""Combined ASGI entrypoint.

Django is initialized first (which runs ``django.setup()``), then the FastAPI
app — which imports Django ORM models — is mounted under ``/api``. Everything
else (e.g. ``/admin``) is handled by Django.

Run with:
    uvicorn upstrah.asgi:application --reload   # from src/
"""
import os

from django.core.asgi import get_asgi_application
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "upstrah.settings.dev")

# Initializes Django (django.setup) before any model import below.
django_application = get_asgi_application()

# Import only after Django is configured.
from starlette.applications import Starlette
from starlette.routing import Mount

from upstrah.api import create_fastapi_app

application = Starlette(
    routes=[
        Mount("/api", app=create_fastapi_app()),
        Mount("/", app=django_application),
    ]
)
