from uuid import UUID

import msgspec

from gilda.core.models import Role
from gilda.planning.schemas import PlanningPeriodSummary, RegistrationRead


class HomeAssociation(msgspec.Struct):
    id: UUID
    name: str
    slug: str
    role: Role
    upcoming: list[RegistrationRead]
    obsolete: list[RegistrationRead]
    planning_period: PlanningPeriodSummary | None
