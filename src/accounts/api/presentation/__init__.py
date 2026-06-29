"""Presentation layer for the accounts app.

The FastAPI-facing layer. Holds ``controllers`` (thin facades extending
:class:`common.api.BaseController` that translate schemas ↔ DTOs and call
one use-case method) and ``schemas`` (Pydantic request/response models —
never domain entities on the wire). Depends on the application + domain
layers; wired to infrastructure via the DI container.
"""
