"""Domain layer for the accounts app.

Pure Python — no Django, FastAPI, Pydantic, httpx, or Celery imports.
Holds the frozen ``entities`` (immutable domain state) and the abstract
``repositories`` (async ports the application layer depends on). Nothing
here reaches upward to application, presentation, or infrastructure.
"""
