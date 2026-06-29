"""Presentation controllers for the academies app.

Thin facades over the use cases, each extending
:class:`common.api.BaseController`. They translate request schemas to DTOs
and entities to response dicts — no business logic, no ORM, no
``APIResponse``.
"""

from academies.api.presentation.controllers.academy_controller import (
    AcademyController,
)
from academies.api.presentation.controllers.membership_controller import (
    MembershipController,
)

__all__ = ["AcademyController", "MembershipController"]
