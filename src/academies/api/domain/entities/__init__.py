"""Domain entities for the academies app.

Frozen ``@dataclass`` representations of the academy and membership
aggregates, decoupled from the Django ORM.
"""

from academies.api.domain.entities.academy import AcademyEntity
from academies.api.domain.entities.membership import MembershipEntity

__all__ = ["AcademyEntity", "MembershipEntity"]
