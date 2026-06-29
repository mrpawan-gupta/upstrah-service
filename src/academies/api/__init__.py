"""Academies API — Clean Architecture entry point for the academies app.

Holds the layered ``api/`` tree for two resource slices — **academy** (a
sports academy CRUD aggregate owned by its creating user) and
**membership** (a user's apply → pending → approved/rejected application to
an academy). Layers run ``presentation → application → domain ←
infrastructure``; the DI container (``infrastructure/di_container.py``)
wires controllers → use cases → repositories at request time, and
``router.py`` mounts the v1 routes under ``/academies/api/v1/...``.
"""
