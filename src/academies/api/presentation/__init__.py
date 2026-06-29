"""Presentation layer for the academies app.

FastAPI-facing controllers (thin facades over the use cases) and Pydantic
request/response schemas for the academy and membership aggregates.
Entities never travel on the wire — schemas do.
"""
