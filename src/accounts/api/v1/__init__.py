"""Accounts API v1 — FastAPI endpoint handlers.

Versioned namespace mounted under ``/accounts/api/v1/`` by
:mod:`accounts.api.router`. Every handler injects its controller via
``Depends(get_<x>_controller)``, calls exactly one controller method, and
wraps the result in ``APIResponse`` (added here, never in the controller).

Routers:
    auth_endpoints         — POST /auth/otp/send, /auth/otp/verify,
                             /auth/refresh, /auth/logout; GET /auth/me
    otp_endpoints          — POST/GET/DELETE /otps (admin)
    user_profile_endpoints — GET/PATCH /users/{user_id}/profile
"""
