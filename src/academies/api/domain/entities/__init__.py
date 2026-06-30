"""Domain entities for the academies app.

Frozen ``@dataclass`` representations of the academy and membership
aggregates, decoupled from the Django ORM. The academy carries the sports
it trains as :class:`SportRef` value objects.
"""

from academies.api.domain.entities.academy import AcademyEntity, SportRef
from academies.api.domain.entities.membership import MembershipEntity

__all__ = ["AcademyEntity", "MembershipEntity", "SportRef"]
