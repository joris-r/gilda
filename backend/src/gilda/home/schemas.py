from dataclasses import dataclass
from uuid import UUID

from gilda.core.models import Role
from gilda.planning.schemas import PlanningPeriodSummary, RegistrationRead


@dataclass
class HomeAssociation:
    """An association as My associations lists it."""

    id: UUID
    name: str
    slug: str
    role: Role
    upcoming: list[RegistrationRead]
    obsolete: list[RegistrationRead]
    planning_period: PlanningPeriodSummary | None
    reminds: bool
