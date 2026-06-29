# upstrah-service

> **API `api/` package conventions — copied verbatim from `rudra-service`.**

---

## `api/` package docstring contract

Every `__init__.py` inside an app's `api/` tree must carry a descriptive module
docstring — `(placeholder)` is a review blocker. Required content per level:

| Package level | Required content |
|---|---|
| `<app>/api/__init__.py` | Full API module description: layers, request flow, structure, import examples |
| Layer packages (`application/`, `domain/`, `infrastructure/`, `presentation/`) | Layer responsibilities, sub-folder map, dependency rule, usage constraints |
| `v1/__init__.py` | Endpoint contract: inject controller via `Depends`, call one method, wrap the result in `APIResponse(data=..., message=..., status=...)` and return it |
| Leaf sub-packages (`dtos/`, `mappers/`, `entities/`, `repositories/`, `value_objects/`, etc.) | One or more sentences: purpose + key constraint |

### Samples (from `care-service`)

**App-level** — `policy/api/__init__.py`:

```python
"""
API Module — CARE Integration API (Clean/Hexagonal Architecture)

Implements the CARE integration API with a four-layer separation of concerns.

Layers:
    1. Presentation (policy.api.presentation/) — handles HTTP requests/responses;
       maps requests to DTOs and invokes use cases.
    2. Application (policy.api.application/)   — business logic in use cases; DTOs.
    3. Domain (policy.api.domain/)             — core entities + repository interfaces.
    4. Infrastructure (policy.api.infrastructure/) — Django-ORM repos, external integrations.

Request flow:
    HTTP Request → Controller (presentation) → DTO (application) → UseCase
        → Repository interface (domain) → Infrastructure impl → Django models
        → response returned back through the layers.
"""
```

**Layer** — `policy/api/application/__init__.py`:

```python
"""
Application Layer — Business Logic and Orchestration

Responsibilities:
    - Implement use cases (business workflows); define + use DTOs across boundaries;
      coordinate repositories; map between layers.

Architecture:
    use_cases/  : workflow implementations      services/ : reusable app services
    dtos/       : inter-layer DTOs              mappers/  : DTO ↔ entity mapping
    interfaces/ : ports for dependency injection

Dependencies: depends on Domain (entities, repo interfaces); used by Presentation.

Rules:
    - Do NOT access the database directly (go through repositories via domain interfaces).
    - Do NOT contain HTTP-specific logic (presentation's job) or framework details.
    - Always use DTOs for input/output; keep use cases single-responsibility.
"""
```

**Versioned namespace** — `policy/api/v1/__init__.py`:

```python
"""
v1 API endpoints and routing for the CARE integration service.

    - Organise endpoints under a versioned namespace.
    - Support multiple API versions simultaneously for backward compatibility.
    - Isolate version-specific logic and schemas.
"""
```

**Leaf sub-package** — `policy/api/presentation/controllers/__init__.py`:

```python
"""
Controllers — HTTP Request Handlers

Receive + validate HTTP requests, then coordinate with the application layer.

Responsibilities: validate via Pydantic schema; map schema → DTO; call the use
case; map entity → DTO → response schema; set HTTP status. No business logic.

Transformation chain:
    Schema → mapper.schema_to_dto() → DTO → use case → entity
        → mapper.entity_to_dto() → DTO → mapper.dto_to_response() → Response Schema → JSON
"""
```

