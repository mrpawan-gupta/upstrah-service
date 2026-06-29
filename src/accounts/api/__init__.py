"""Accounts API — Clean Architecture entry point for the accounts app.

This package holds the layered ``api/`` tree for three resource slices —
**auth** (phone → OTP → JWT login), **otp** (the OTP resource backing the
flow), and **user_profile** (onboarding demographics + role). Layers run
``presentation → application → domain ← infrastructure``; the DI container
(``infrastructure/di_container.py``) wires controllers → use cases →
repositories at request time, and ``router.py`` mounts the v1 routes under
``/accounts/api/v1/...``.
"""
