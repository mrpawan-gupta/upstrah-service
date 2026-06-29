"""Versioned (v1) API namespace for the academies app.

Holds the FastAPI endpoint routers for the academy and membership
resources and the ``router`` that mounts them under ``/api/v1``. The
app-level router (:mod:`academies.api.router`) mounts this under
``/academies``, so the final paths are ``/academies/api/v1/...``.
"""
