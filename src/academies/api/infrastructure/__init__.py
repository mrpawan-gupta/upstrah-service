"""Infrastructure layer for the academies app.

Django-ORM repository adapters and the DI container that wires
repositories → use cases → controllers. Re-exports the controller
factories endpoints depend on via ``Depends(...)``.
"""

from academies.api.infrastructure.di_container import (
    di_container,
    get_academy_controller,
    get_membership_controller,
)

__all__ = ["di_container", "get_academy_controller", "get_membership_controller"]
