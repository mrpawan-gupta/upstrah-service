# CLAUDE.md — upstrah-service

> **API creation rules — copied verbatim from `rudra-service`** (the reference Rama service).
> Follow these exactly when building any API in this service.

---

### Clean Architecture inside each Django app — the `api/` skeleton

Every Django app owns a local `api/` tree. The shape is identical in every
service and every app; the DI container wires controllers to use cases to
repositories at request time.

```
<app>/api/
├── v1/                          # FastAPI routers + endpoint functions
│   ├── router.py                # mounts the app's v1 sub-routes into one APIRouter
│   └── <domain>_endpoints.py    # async def endpoints; thin — call controller + return envelope
├── domain/                      # Pure Python, no Django, no FastAPI
│   ├── entities/                # @dataclass — pure state, no ORM/Pydantic
│   ├── events/                  # DomainEvent subclasses
│   └── repositories/            # Abstract async interfaces
├── application/                 # Use cases; no ORM, no FastAPI
│   ├── use_cases/               # one class per aggregate
│   ├── dtos/                    # plain dataclasses for use-case input/output
│   ├── mappers/                 # entity ↔ DTO conversion; never entity ↔ ORM
│   ├── services/                # application services that combine multiple repos
│   └── interfaces/              # additional ports
├── infrastructure/              # Adapters — Django ORM, external APIs, DI wiring
│   ├── repositories/            # concrete *RepositoryImpl implementing domain interfaces
│   ├── external_services/       # external HTTP/SDK clients (SMS, email)
│   ├── external/                # provider routers (SMS, email provider selection)
│   ├── di_container.py          # DIContainer with lazy singletons; get_*_controller() factories
│   └── config/                  # service-specific wiring
└── presentation/                # FastAPI-facing layer
    ├── controllers/             # thin facades; extend common.api.BaseController
    └── schemas/                 # Pydantic request/response schemas; never entities on the wire
```

**Dependency direction.** `presentation → application → domain ← infrastructure`. The domain layer imports nothing from Django, FastAPI, Pydantic, httpx, or any peer package. Application imports only domain. Presentation and infrastructure both depend on application + domain and are wired together in `infrastructure/di_container.py`.

### API design contract (mandatory for every Rama service)

These rules apply to every Rama service exposing a FastAPI surface — controllers and routers across services must look interchangeable.

#### API design — strict rules (non-negotiable)

Each rule below is a **review blocker**: a PR that violates one does not merge. "MUST" / "MUST NOT" are literal.

1. **Layering is one-directional.** `presentation → application → domain ← infrastructure`. The **domain** layer MUST NOT import Django, FastAPI, Pydantic, httpx, Celery, or any peer package. **application** imports only domain (+ `common`). ORM access MUST NOT appear above `infrastructure`. A layer reaching upward is a blocker.
2. **One file per resource per layer.** Exactly: `domain/entities/<x>.py`, `domain/repositories/<x>_repository.py`, `application/dtos/<x>_dtos.py`, `application/mappers/<x>_mapper.py`, `application/use_cases/<x>_use_cases.py`, `infrastructure/repositories/<x>_repository_impl.py`, `presentation/schemas/<x>_schemas.py`, `presentation/controllers/<x>_controller.py`, `v1/<x>_endpoints.py`. No multi-resource "god" modules.
3. **Inherit the `common/api` bases — never duplicate.** Controller→`BaseController`, use case→`BaseUseCase`, repository→`BaseRepository`. **Override** a slot to change shape; **add** a sibling method only when the base signature genuinely can't carry the need (tenant scope, non-int id, audit transition). A `get_x()` that re-implements inherited `get()` is a blocker.
4. **Schema bases are mandatory.** Request schemas extend `BaseRequestSchema` (`extra="forbid"`). Response schemas extend `BaseResponseSchema` (`from_attributes=True`). List filters extend `BaseFilter`. Entities extend `BaseEntity` (frozen `@dataclass`); DTOs extend `BaseModelDTO`. PUT schemas = all fields required; PATCH schemas = all fields `| None = None`. Validation lives in the schema, never the controller.
5. **The mapper is the only serialization boundary.** `model_dump()` MUST appear **only** inside a mapper (`schema_to_dto` / `dto_to_response`) — never in a controller body, use case, repository, or endpoint. `orm_to_entity` MUST return a frozen entity and MUST NOT leak an ORM object upward.
6. **Each layer's single job.** Controller = DTO/schema translation + one use-case call (zero business logic, zero ORM). Use case = business rules/validation/dispatch (no `model_dump`, no FastAPI). Repository = data access only (NO Celery, NO HTTP, NO business rules). Endpoint = inject + call one method + wrap `APIResponse` (no logic).
7. **DI is fixed.** Exactly one `async def get_<x>_controller(...) -> XController` per controller; endpoints obtain it **only** via `Depends(get_<x>_controller)`. Constructing a controller inside an endpoint is a blocker. Every controller MUST be reachable from a mounted route.
8. **The envelope is added at the endpoint, once.** Controllers return the inner payload; the endpoint wraps `APIResponse(data=, message=_(...), status=)`. All user-facing messages use `gettext_lazy as _`. Never build `APIResponse` in a controller.
9. **Pagination is standardized.** List endpoints use `offset: int = Query(0, ge=0)` + `limit: int = Query(20, ge=1, le=100)`; controllers return `tuple[list[dict], OffsetPaginatedResponse]`; the endpoint passes pagination through as `meta=`. `limit > 100` is rejected at the boundary.
10. **Tenancy is explicit.** Scoped reads/writes thread `company_ids: list[int]` (from `get_company_ids`) end-to-end. Repositories use the scoped `Model.objects`; `Model.objects_all` is allowed **only** in migrations/admin/cross-tenant jobs. Scoped models carry `company_id: BigIntegerField(db_index=True)` — never an FK across services.
11. **Side effects go through the right door.** External calls use a `common/services/dispatch.py` dispatcher (circuit-breaker guarded) — **never raw `httpx`**. Celery: `.apply_async(kwargs=..., queue=...)` only (never `.delay()`), invoked only from a use case or a `BaseCeleryDispatcher` subclass — never models/signals/serializers/views/repositories.
12. **Errors are typed + centralized.** Raise `common/exceptions` `AppBaseError` subclasses (`ValidationError`, `NotFoundError`, `AuthenticationError`, …); the universal exception handler renders the envelope. Do not scatter ad-hoc `HTTPException` / bare `Response`.
13. **Storage & history rules hold.** No `FileField`/`ImageField` (document ids → lekha; `Company.icon` is the one documented exception). No lifecycle `*_at` columns on business rows — keep `status`, write transitions to `tracer.Activity`.
14. **URLs & docstrings.** Resources are plural kebab-case; final path `/<app>/api/v1/<resource>/`. Every `api/`-tree `__init__.py` has a real docstring (`(placeholder)` is a blocker); every endpoint documents `Args` / `Returns` / explicit HTTP status.

#### App scaffold — strict rules

1. **Follow the file tree exactly** (see [Required scaffold](#required-scaffold-file-tree)). Do not invent alternate folder names or skip layers — even a trivial resource gets all five layers.
2. **Build inside-out** in the [Build order](#build-order-inside-out): entity → repo interface → DTOs → mapper → use case → repo impl → DI → schemas → controller → endpoints → migrations → docstrings → tests → OpenAPI check. Don't start at the endpoint.
3. **Re-export through every `__init__.py`** and give each new package `__init__.py` a real docstring describing the layer (table in [docstring contract](#api-package-docstring-contract)).
4. **Wire it end-to-end before merge:** app router included in the project router; `v1` router mounted under `/<app>/`; `get_<x>_controller` referenced by a mounted handler. An unreachable controller/route is a blocker.
5. **Migrations reviewed:** `db_index=True` on `company_id` and FK-shaped `BigIntegerField`s; no `*_at` lifecycle columns; soft-delete via `SoftDeleteMixin`.
6. **Tests are part of the scaffold, not optional:** a mapper round-trip test, a use-case test with a fake repository, and a FastAPI integration test against a real DB transaction.

#### `api/` package docstring contract

Every `__init__.py` inside an app's `api/` tree MUST carry a descriptive module docstring — `(placeholder)` is a review blocker. The required content per package level, with **real sample docstrings from care-service**, is in the [README](./README.md#api-package-docstring-contract).

#### Controller CRUD method patterns

A controller method is a thin facade: map the request schema → DTO (mapper), call
**one** use-case method, map the returned entity → DTO → response (mapper), and
return that inner payload — the endpoint adds the `APIResponse` envelope. No
business logic, no ORM, no `model_dump()` in the body. Scoped reads/writes thread
`company_ids` end-to-end. The fixed transformation chain:

```
Schema → mapper.schema_to_dto() → DTO → use case → entity
       → mapper.entity_to_dto() → DTO → mapper.dto_to_response() → ResponseSchema
```

**Standard CRUD** (rudra's `accounts` app is the canonical reference):

```python
async def get(self, id_: int, *, company_ids: list[int]) -> XResponseSchema:
    """Retrieve a <resource> by ID (GET)."""
    entity = await self.use_cases.get_scoped(id_, company_ids=company_ids)
    return XMapper.dto_to_response(XMapper.entity_to_dto(entity))

async def update(self, id_: int, request: XUpdateSchema, company_ids: list[int]) -> XResponseSchema:
    """Full replace (PUT) — every field overwrites."""
    entity = await self.use_cases.update(
        id_=id_, dto=XMapper.update_schema_to_dto(request), company_ids=company_ids
    )
    return XMapper.dto_to_response(XMapper.entity_to_dto(entity))

async def partial_update(self, id_: int, request: XPatchSchema, company_ids: list[int]) -> XResponseSchema:
    """PATCH — unset fields are left unchanged."""
    entity = await self.use_cases.partial_update(
        id_=id_, dto=XMapper.patch_schema_to_dto(request), company_ids=company_ids
    )
    return XMapper.dto_to_response(XMapper.entity_to_dto(entity))

async def destroy(self, id_: int, company_ids: list[int]) -> None:
    """Soft-delete (DELETE) — never hard-deletes (audit trail)."""
    await self.use_cases.destroy(id_=id_, company_ids=company_ids)

async def list(
    self, offset: int, limit: int, company_ids: list[int], **filters: Any
) -> tuple[list[dict], OffsetPaginatedResponse]:
    """Paginated list (GET) — returns (items, pagination) for the endpoint to emit as meta."""
    entities, pagination = await self.use_cases.list(
        offset=offset, limit=limit, company_ids=company_ids, filters=filters
    )
    return [
        XMapper.dto_to_response(XMapper.entity_to_dto(e)).model_dump() for e in entities
    ], pagination
```

**Async-create (202)** — CARE-bridged / async resources persist a draft and return
immediately; a post-save signal enqueues the Celery workflow and the outcome is
fanned out via Kriya:

```python
async def create(self, request: XRequestSchema, company_id: int) -> dict:
    """Accept the request and return 202 (POST) — persists the draft; a signal enqueues the workflow."""
    entity = await self.use_cases.create(dto=XMapper.schema_to_dto(request), company_id=company_id)
    return {"draft_id": entity.id, "status": entity.status}
```

#### Common-base inheritance (mandatory)

Every layer of every resource is built on a shared base from `common/api/` — import these, never hand-roll an equivalent. `common/api/` is owned by rudra and synced verbatim to every service, so the contract is identical everywhere.

##### CRUD bases — the three-layer spine

`BaseController` / `BaseUseCase` / `BaseRepository` share one async CRUD surface — `get`, `create`, `update`, `partial_update`, `delete`, `bulk_delete`, `bulk_patch`, `list`, `list_cursor` (the repository adds `count`). Each layer's default methods proxy to the layer below: **controller → use case → repository**, so an untouched resource needs almost no code.

The rule is **inherit-and-override, never duplicate**:

- **Inherit** the base surface as-is when the default fits.
- **Override** a slot (same name) when its shape must change — a controller `get` that maps entity → response schema, a use case `create` that enforces an invariant, a repository `delete` that soft-deletes.
- **Add** a sibling method *only* when the base signature genuinely can't carry the need (tenant scope `company_ids: list[int]`, a non-int id, an audit-writing transition, a resource-specific read). Re-implementing a base method under a new name (a `get_x` that does what `get` already does) is a **review blocker** — call or override the base.

| Layer | Base | Sets / overrides |
|---|---|---|
| Controller (`presentation/controllers/`) | `BaseController` | Override CRUD slots to translate entity → response schema; add scoped/domain methods on top. |
| Use case (`application/use_cases/`) | `BaseUseCase` | Override CRUD to add domain rules, validation, dispatcher fan-out; add orchestration methods. |
| Repository (`infrastructure/repositories/`) | `BaseRepository` | Declare `model = <ORM>` (+ optional `default_ordering`); override for `select_related` / soft-delete; add scoped-query methods. |

A controller that genuinely fronts several `ReqDTO` / `RespDTO` pairs (no single CRUD shape fits) may compose multiple use cases instead of inheriting one base — **document the exception in the module docstring**.

##### Building-block bases — what each layer's objects extend

| Symbol (`common/api/`) | Used in | Purpose / contract |
|---|---|---|
| `BaseEntity` | `domain/entities/` | Frozen `@dataclass` base for domain entities; provides `to_dict()`. Declares no fields, so subclass field order is free. Subclass MUST be `@dataclass(frozen=True)`. |
| `BaseModelDTO` | `application/dtos/` | Base for mutable DTO dataclasses; `to_dict()` / `from_dict()` so use cases/mappers serialise to ORM `**fields` and rebuild. Subclass owns the `@dataclass` decorator. |
| `BaseRequestSchema` | `presentation/schemas/` (request) | Pydantic base with `extra="forbid"` — unknown fields raise 422 instead of being silently dropped. PUT = all required; PATCH = all `\| None`. |
| `BaseResponseSchema` | `presentation/schemas/` (response) | Pydantic base with `from_attributes=True` — a mapper builds it straight from an entity/ORM row via `model_validate(obj)`. |
| `BaseFilter` | `v1/` list endpoints (`Depends()`) | Pydantic list-query base: `limit` (1–200, default 20), `offset`, `search`, `sort_by`, `sort_order` (`asc\|desc`). `to_orm_filters()` → `.filter(**kwargs)` (excludes paging/sort/search + `None`s); `to_order_by()` → ORM `order_by` list. Subclass adds resource-specific filter fields. |

##### Response envelope (`common/api/response.py`)

| Symbol | Purpose |
|---|---|
| `APIResponse[DataT]` | The wire envelope `{data, message, status, success, meta}` — used as the FastAPI `response_model`. `success` is derived from `status` (2xx → true); a default `message` is filled per status. **Built only at the endpoint.** |
| `OffsetPaginatedResponse` | List-endpoint `meta`: `{limit, offset, total, returned, has_more}`. Controllers return `tuple[list[dict], OffsetPaginatedResponse]`; the endpoint passes it as `meta=`. |
| `BulkDeletePayload` | Bulk-delete request body `{ids: list[int]}`. |
| `BulkPatchPayload` | Bulk-patch request body `{ids: list[int], is_active: bool}`. |

All of the above are importable from `common.api` directly (re-exported in `common/api/__init__.py`).

#### Mapper class pattern

Every mapper in `application/mappers/` is a class with **static methods** covering both write and entity-read paths.

```python
class XMapper:
    # Write path
    @staticmethod
    def schema_to_dto(schema: XCreateSchema) -> XCreateDTO:
        return XCreateDTO(field=schema.field, ...)

    @staticmethod
    def patch_schema_to_dto(schema: XUpdateSchema) -> XUpdateDTO:
        return XUpdateDTO(field=schema.field, ...)  # unset fields remain None

    # Entity-based read path
    @staticmethod
    def orm_to_entity(row: Any) -> XEntity:
        return XEntity(id=row.id, ...)  # no ORM object escapes this boundary

    @staticmethod
    def entity_to_dto(entity: XEntity) -> XResponseDTO:
        return XResponseDTO(id=entity.id, ...)

    @staticmethod
    def dto_to_response(dto: XResponseDTO) -> dict:
        return XResponseSchema.model_validate(dto, from_attributes=True).model_dump(mode="json")
```

Rules:

- `model_dump()` is called only inside `schema_to_fields`, `patch_schema_to_fields`, or `dto_to_response`. Never in a controller body or use case.
- `orm_to_entity` must never leak an ORM object — always return a frozen `@dataclass` entity.
- For nested resources, compose child mappers explicitly rather than calling `model_dump()` inline.
- Add `merge_update_dtos` / `merge_patch_dtos` when a full-replace or selective-merge operation needs to compare old vs new DTO.
- Split mappers one file per top-level entity under `application/mappers/` (e.g. `policy_mapper.py`, `vehicle_mapper.py`).

#### v1 router & endpoint conventions

```python
# <app>/api/v1/endpoints.py
from fastapi import APIRouter, Depends, Query
from django.utils.translation import gettext_lazy as _

from common.api.response import APIResponse, OffsetPaginatedResponse
from common.auth.dependencies import get_company_ids, require_partner_or_user
from common.auth.jwt.token_user import TokenUser

router = APIRouter(prefix="/api/v1", tags=["<resource>"])
```

The app-level router mounts this under `/<app>/`, so the final path is `/<app>/api/v1/<resource>/`.

**Controllers inherit from `common.api.BaseController`** — the shared async CRUD facade (`get` / `create` / `update` / `partial_update` / `delete` / `bulk_delete` / `bulk_patch` / `list` / `list_cursor`), whose default methods proxy to the injected use case. Override the slots whose response shape differs and add scoped/domain methods on top; see [Common-base inheritance](#common-base-inheritance-mandatory) for the full inherit-and-override rule.

**Endpoint body shape — always wrap in `APIResponse`:**

```python
@router.get("/<resource>/{id_}", response_model=APIResponse)
async def get_resource(
    id_: int,
    _caller: TokenUser = Depends(require_partner_or_user),
    controller: XController = Depends(get_x_controller),
    company_ids: list[int] = Depends(get_company_ids),
) -> APIResponse:
    """Retrieve a <resource> by ID."""
    return APIResponse(
        data=await controller.get(id_, company_ids=company_ids),
        message=_("<Resource> {id_} retrieved successfully").format(id_=id_),
        status=200,
    )
```

Rules that bind every endpoint:

- **Wrap with `APIResponse(...)` at the endpoint** — never in the controller. The controller returns the inner payload; the endpoint adds the envelope.
- **All user-facing message strings use `gettext_lazy as _`** (from `django.utils.translation`) — even inside FastAPI handlers. Use `.format(...)` so translations stay extractable.
- **Auth dependencies live in `common.auth.dependencies`** — `require_partner_or_user`, `require_user`, `get_company_ids`. Inject via `Depends(...)`.
- **Underscore-prefix the auth dep param** when only token validation is needed: `_caller: TokenUser = Depends(require_partner_or_user)`.
- **Async-create endpoints (202-pattern) MUST set `status_code=202`** in the route decorator AND `status=202` in the `APIResponse`. Return shape: `{"draft_id": <int>, "status": "pending"}`.
- **Pagination params**: `offset: int = Query(0, ge=0, description="Pagination offset")` and `limit: int = Query(20, ge=1, le=100, description="Items per page")`. `limit > 100` is rejected at the framework boundary.
- **List endpoints emit pagination meta in the envelope** — controller returns `tuple[list[dict], OffsetPaginatedResponse]`; endpoint passes the pagination object straight through as `meta=...`:

```python
items, pagination = await controller.list(offset=offset, limit=limit, company_ids=company_ids, ...)
return APIResponse(
    data=items,
    message=_("<Resources> retrieved successfully"),
    status=200,
    meta=pagination,
)
```

- **Endpoint docstrings document `Args:`, `Returns:`, and the explicit HTTP status** — populates Swagger/Redoc descriptions.

#### Dependency injection & controller wiring (mandatory)

Wiring is the **only** place the three layers meet. Each app has exactly one `infrastructure/di_container.py` holding one `DIContainer` and one `get_<x>_controller` factory per controller. The container assembles the dependency graph **repository → use case → controller**; endpoints obtain the controller **only** through `Depends(get_<x>_controller)`. Nothing else — no endpoint, model, signal, or use case — instantiates a repository, use case, or controller.

##### How the `DIContainer` must be structured

```python
# <app>/api/infrastructure/di_container.py
from <app>.api.application.use_cases import XUseCases
from <app>.api.domain.repositories import IXRepository
from <app>.api.infrastructure.repositories import XRepositoryImpl
from <app>.api.infrastructure.services import CeleryXDispatcher
from <app>.api.presentation.controllers import XController


class DIContainer:
    """Single composition root for the <app> app. One typed slot per collaborator; lazy + memoised."""

    def __init__(self) -> None:
        """Initialise every cached component slot to ``None``."""
        self._x_repository: IXRepository | None = None
        self._x_dispatcher: CeleryXDispatcher | None = None
        self._x_use_cases: XUseCases | None = None
        self._x_controller: XController | None = None

    async def get_x_repository(self) -> IXRepository:
        if self._x_repository is None:
            self._x_repository = XRepositoryImpl()
        return self._x_repository

    async def get_x_dispatcher(self) -> CeleryXDispatcher:
        if self._x_dispatcher is None:
            self._x_dispatcher = CeleryXDispatcher()
        return self._x_dispatcher

    async def get_x_use_cases(self) -> XUseCases:
        if self._x_use_cases is None:
            self._x_use_cases = XUseCases(
                repository=await self.get_x_repository(),
                dispatcher=await self.get_x_dispatcher(),
            )
        return self._x_use_cases

    async def get_x_controller(self) -> XController:
        if self._x_controller is None:
            self._x_controller = XController(await self.get_x_use_cases())
        return self._x_controller


di_container = DIContainer()  # one module-level instance per app


async def get_x_controller() -> XController:
    """FastAPI dependency — the ONLY way an endpoint gets an XController."""
    return await di_container.get_x_controller()
```

**Caching is one explicit typed slot per collaborator.** Each collaborator is a
`self._x: IX | None = None` attribute set in `__init__`; its `async def
get_x_*()` accessor builds it on first call (`if self._x is None:`) and returns
the cached instance thereafter. **Never use `functools.cached_property` or
`functools.lru_cache` in a `di_container`, and never collapse the slots into a
generic `_instances` dict** — the explicit per-slot form is the single uniform
pattern across every app (rudra's `accounts` container is the reference), so
every container reads identically and each cached collaborator is individually
typed and inspectable.

##### Strict DI rules (review blockers)

1. **One container per app.** Exactly one `DIContainer` in `infrastructure/di_container.py` is the composition root. No second container, no per-resource container, no global mutable registry.
2. **One slot per collaborator; no duplicates.** Each repository / dispatcher / HTTP client gets exactly one slot. A second instance of the same collaborator built anywhere else is a blocker.
3. **Singletons are lazy + memoised via explicit typed slots.** Each stateless, long-lived collaborator (repository, dispatcher, HTTP client) is a `self._x: IX | None = None` slot in `__init__`, cached on first access by its `async def get_x_*()` method (`if self._x is None:`) — never built at import time, never re-created per request. **`functools.cached_property`, `lru_cache`, and a generic `_instances` dict are all banned in a `di_container`** — use the explicit per-slot form (rudra's `accounts` container is the reference) so every container caches identically and each slot stays individually typed.
4. **The container only wires — it holds no logic.** No business rules, no I/O, no request/tenant state (`company_ids` is a method argument threaded at call time, never stored on the container). Constructor injection only — collaborators are passed in `__init__`, never reached for via a global inside a method.
5. **Exactly one `async def get_<x>_controller() -> XController` per controller**, and its name + signature are fixed so routers stay interchangeable across services. It returns `container.x_controller()` and nothing more.
6. **Endpoints inject only via `Depends(get_<x>_controller)`.** Constructing a controller, use case, or repository inside an endpoint (or importing the container into an endpoint module) is a blocker.
7. **Depend on interfaces, not impls.** Use cases type their collaborators as the domain interface (`IXRepository`, `IXDispatcher`); the container is the single place a concrete impl is named — so a fake can be substituted in tests by swapping one slot.
8. **Every controller is reachable.** Each `get_<x>_controller` is referenced by at least one mounted `@router.<verb>` handler, and the app router is included in the project router. An unreferenced factory or unmounted controller is a blocker.

#### Designing a new API: scaffold + workflow

When adding a new resource (or new endpoint on an existing resource), follow this scaffold and workflow. **rudra-service's `accounts` app is the canonical reference** — the most complete `api/` tree in the ecosystem; mirror its layout.

##### Decide up front

| Question | Why |
|---|---|
| Resource name? (plural noun, kebab-case in URLs) | Determines URL path, controller name, DTO/entity names |
| Who calls it? (user JWT, partner JWT, or both) | Picks the auth dep: `require_user` / `require_partner_or_user` |
| Data scoped per-company? | Decides whether `get_company_ids` is injected, models extend `ScopedManager` |
| Sync or async (202-pattern)? | Async-create returns 202 + enqueues Celery; sync endpoints return 200/201 |
| External/3rd-party calls involved? | Use a dispatcher from `common/services/dispatch.py` — never raw `httpx` |
| Stores documents? | All file storage goes through `lekha-service`; persist `lekha_document_id: BigIntegerField` locally |
| Soft-delete or hard-delete? | Soft-delete requires `SoftDeleteMixin`; hard-delete is rare and audit-trail justified |
| Filters / pagination? | All list endpoints use the standard `offset`/`limit` + `OffsetPaginatedResponse` meta |

##### Required scaffold (file tree)

For a new resource `<X>` in app `<app>`, create the following. Files marked **N** are new; existing `__init__.py` files just get a new re-export.

```
<app>/api/
├── __init__.py                                         # module docstring (full API overview)
├── router.py                                           # mounts v1 under /<app>/  (one-time per app)
├── domain/
│   ├── entities/
│   │   ├── __init__.py                                 # re-export X
│   │   └── x.py                                    [N] # frozen @dataclass entity (BaseEntity)
│   ├── repositories/
│   │   ├── __init__.py                                 # re-export IXRepository
│   │   └── x_repository.py                         [N] # abc.ABC with abstract methods
│   ├── events/__init__.py                              # DomainEvent subclasses (only if X emits events)
│   └── value_objects/__init__.py
├── application/
│   ├── dtos/
│   │   ├── __init__.py                                 # re-export DTOs
│   │   └── x_dtos.py                               [N] # XCreateDTO, XUpdateDTO, XPatchDTO, XResponseDTO (BaseModelDTO)
│   ├── mappers/
│   │   ├── __init__.py                                 # re-export XMapper
│   │   └── x_mapper.py                             [N] # static-method mapper class
│   ├── use_cases/
│   │   ├── __init__.py                                 # re-export XUseCases
│   │   └── x_use_cases.py                          [N] # XUseCases(BaseUseCase) — business orchestration
│   ├── services/__init__.py                            # reusable application services if needed
│   └── interfaces/__init__.py                          # ports (dispatcher/service interfaces) for DI
├── infrastructure/
│   ├── __init__.py                                     # re-export di_container + factories
│   ├── di_container.py                                 # add lazy singletons + Depends factory for the controller
│   ├── repositories/
│   │   ├── __init__.py                                 # re-export XRepositoryImpl
│   │   └── x_repository_impl.py                    [N] # XRepositoryImpl(BaseRepository) — Django ORM impl
│   ├── persistence/__init__.py                         # ORM managers / shared query helpers (optional)
│   ├── services/__init__.py                            # concrete service impls (e.g. a BaseCeleryDispatcher subclass)
│   ├── external/__init__.py                            # direct 3rd-party HTTP/SDK clients (only if hitting an API directly)
│   ├── external_services/                              # provider-selecting adapters (optional)
│   │   ├── notifications/__init__.py                   #   SMS / email / push routers
│   │   └── storage/__init__.py                         #   file/object-storage adapters
│   └── config/__init__.py                              # app-local DI/config constants
├── presentation/
│   ├── controllers/
│   │   ├── __init__.py                                 # re-export XController
│   │   ├── base_controller.py                          # one-time per app: abc.ABC enforcing CRUD surface
│   │   └── x_controller.py                         [N] # XController(BaseController) — thin facade
│   └── schemas/
│       ├── __init__.py                                 # re-export X*Schema
│       └── x_schemas.py                            [N] # Pydantic schemas
└── v1/
    ├── __init__.py                                     # versioned-namespace docstring
    └── endpoints.py                                    # add new @router.<verb> handlers for X
```

Mount path: top-level project router includes `<app>.api.router`, whose `APIRouter(prefix="/<app>")` includes `v1.endpoints.router` (`prefix="/api/v1"`). Final URL: `/<app>/api/v1/<resource>/`.

##### Build order (inside-out)

1. **Domain entity** — `domain/entities/x.py`: frozen `@dataclass(frozen=True)`. No ORM, no I/O.
2. **Repository interface** — `domain/repositories/x_repository.py`: `class IXRepository(abc.ABC):` with abstract methods. Returns entities, never ORM rows.
3. **DTOs** — `application/dtos/x_dtos.py`: `XCreateDTO`, `XUpdateDTO`, `XPatchDTO`, `XResponseDTO`. Frozen dataclasses; `XPatchDTO` uses `| None` defaults.
4. **Mapper** — `application/mappers/x_mapper.py`: static methods per the mapper pattern above.
5. **Use case** — `application/use_cases/x_use_cases.py`: takes repo (typed as `IXRepository`) + dispatchers in `__init__`. Always pass `company_ids: list[int]` for scoped reads/writes. Enqueue Celery tasks via `.apply_async(kwargs={...}, queue="<q>")`, never `.delay()`.
6. **Repository impl** — `infrastructure/repositories/x_repository_impl.py`: `class XRepositoryImpl(IXRepository):`. Wrap ORM in `sync_to_async(thread_sensitive=True)` or use native async ORM. Map rows to entities via `XMapper.orm_to_entity`. Use `Model.objects` (scoped) for reads; `Model.objects_all` only in migrations/admin.
7. **DI container wiring** — `infrastructure/di_container.py`: add `_x_repository`, `_x_use_cases`, `_x_controller` slots; lazy getters; module-level `get_x_controller()` async function for FastAPI `Depends(...)`.
8. **Pydantic schemas** — `presentation/schemas/x_schemas.py`: `XRequestSchema` (POST), `XResponseSchema` (GET), `XUpdateSchema` (PUT — all fields required), `XPatchSchema` (PATCH — all fields `| None = None`). Validators here, not in the controller.
9. **Controller** — `presentation/controllers/x_controller.py`: `class XController(BaseController):` with `__init__(self, x_use_cases: XUseCases)`. One method per HTTP verb. Zero business logic — only DTO ↔ schema translation and use-case calls.
10. **Endpoint handlers** — append `@router.<verb>(...)` functions in `v1/endpoints.py` following the conventions above.
11. **Migrations** — `make makemigrations`, then review SQL for `db_index=True` on `company_id` and any FK-shaped `BigIntegerField`s.
12. **Update `__init__.py` docstrings** — every new package directory needs a real docstring (no `(placeholder)`).
13. **Tests** — at minimum: mapper unit test (round-trip schema→DTO→entity→response), use-case unit test (with fake `IXRepository`), integration test against the FastAPI endpoint with a real DB transaction. Mark slow tests `@pytest.mark.slow`.
14. **OpenAPI sanity-check** — visit `/api/swagger/` locally and confirm new routes appear with correct request/response models and status codes.

##### Request flow at runtime

```
HTTP request
  → FastAPI router (v1/endpoints.py)
  → Auth dep validates JWT (require_partner_or_user)
  → get_company_ids resolves scope from JWT or X-Company-IDs header
  → DI factory provides controller instance (singleton, lazy)
  → Endpoint calls controller.<verb>(request_schema, company_ids=...)
  → Controller: XMapper.schema_to_dto(request)
  → Controller: await use_cases.<verb>(dto, company_ids=...)
      → UseCase: repo.<op>(...) returns entity (via XMapper.orm_to_entity)
      → UseCase: optional dispatcher call (RudraDispatcher / KriyaDispatcher / etc.)
      → UseCase returns entity
  → Controller: XMapper.dto_to_response(XMapper.entity_to_dto(entity))
  → Endpoint wraps result in APIResponse(data=..., message=_(...), status=200, meta=...)
  → Response back through middleware (request_id, trace_id, correlation_id headers)
```

##### Pre-merge checklist (full API-design audit)

A line-by-line audit of the strict rules above, grouped by layer. Every box must be tickable or the PR is blocked.

**Layering & structure**

- [ ] `domain/` imports no Django / FastAPI / Pydantic / httpx / Celery / peer packages.
- [ ] No ORM access above `infrastructure/`; no layer imports upward.
- [ ] Exactly one file per resource per layer; no multi-resource modules.
- [ ] Every new `api/`-tree `__init__.py` has a real docstring + re-exports its symbols.

**Domain**

- [ ] Entity is a frozen `@dataclass` extending `BaseEntity`; scalar fields only.
- [ ] Repository interface is an `abc.ABC` returning entities (never ORM rows).

**Application**

- [ ] DTOs extend `BaseModelDTO`; `XPatchDTO` fields default `| None`.
- [ ] Mapper is a static-method class; `orm_to_entity` returns a frozen entity (no ORM leak).
- [ ] `model_dump()` appears **only** inside a mapper.
- [ ] Use case inherits `BaseUseCase`, holds business rules, threads `company_ids`, calls dispatchers for side effects; no `model_dump`, no FastAPI, no raw ORM.

**Infrastructure**

- [ ] Repository inherits `BaseRepository`, sets `model` (+ `default_ordering`); data access only — no Celery, no HTTP, no business rules.
- [ ] Scoped reads use `Model.objects`; `Model.objects_all` only in migrations/admin.
- [ ] One `get_<x>_controller` factory wiring repo → use case → controller.

**Presentation (controller)**

- [ ] Controller inherits `BaseController`; one method per verb; DTO/schema translation only — zero business logic, zero ORM, no `APIResponse`.
- [ ] Base methods overridden (not duplicated under new names); siblings added only when the base signature can't carry the need.

**Presentation (schemas)**

- [ ] Request schemas extend `BaseRequestSchema` (`extra="forbid"`); responses extend `BaseResponseSchema` (`from_attributes=True`); filters extend `BaseFilter`.
- [ ] PUT schema all-required; PATCH schema all-optional; validators live in the schema.

**Endpoints (v1)**

- [ ] Endpoint injects the controller via `Depends(get_<x>_controller)` — never instantiates it.
- [ ] `APIResponse(...)` wrapped at the endpoint only; messages use `gettext_lazy as _`.
- [ ] Auth dep injected (`require_user` / `require_partner_or_user`); `get_company_ids` for scoped resources.
- [ ] List: `offset`/`limit` (`ge`/`le` bounds) + returns `(items, OffsetPaginatedResponse)` passed as `meta=`.
- [ ] 202-pattern endpoints set `status_code=202` **and** `status=202`, returning `{"draft_id", "status"}`.
- [ ] Endpoint docstring documents `Args` / `Returns` / HTTP status; resource URL is plural kebab-case.
- [ ] Controller is reachable: route mounted, app router included in the project router.

**Cross-cutting**

- [ ] External calls via a `dispatch.py` dispatcher — no raw `httpx`.
- [ ] Celery: `.apply_async(kwargs=, queue=)` only (no `.delay()`), only in a use case / `BaseCeleryDispatcher`.
- [ ] Errors raise `common/exceptions` `AppBaseError` subclasses (no scattered `HTTPException`).
- [ ] No `FileField`/`ImageField` (ids → lekha); no `*_at` lifecycle columns; `company_id` is `BigIntegerField(db_index=True)`, no cross-service FK.

**Tests & verification**

- [ ] Mapper round-trip test + use-case test (fake repo) + FastAPI integration test (real DB txn).
- [ ] OpenAPI at `/api/swagger/` shows the new routes with correct models/status.
- [ ] `make pre-push` passes.
