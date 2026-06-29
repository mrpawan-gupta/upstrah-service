"""Django URLs. The JSON API is served by FastAPI (mounted in upstrah/asgi.py);
Django here only owns the admin site."""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
