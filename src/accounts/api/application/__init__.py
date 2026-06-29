"""Application layer for the accounts app.

Orchestrates the domain to satisfy use cases. Imports only the domain
layer (plus ``common``) — never Django ORM, FastAPI, or infrastructure.
Holds ``dtos`` (use-case boundary dataclasses), ``mappers`` (entity ↔ DTO
↔ response, the only serialization boundary), ``use_cases`` (business
rules), and ``interfaces`` (additional ports such as the OTP dispatcher).
"""
