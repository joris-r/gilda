from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import Role, User
from gilda.core.repositories import MembershipRepository
from gilda.home.schemas import HomeAssociation
from gilda.planning.services import PlanningService


class HomeService:
    """Gathers what each domain shows of an association on My associations."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.memberships = MembershipRepository(session=db_session)
        self.planning = PlanningService(db_session)

    async def list_for(self, user: User) -> list[HomeAssociation]:
        associations = []
        for membership in await self.memberships.list(user_id=user.id):
            planning = await self.planning.summary(user, membership.association)
            associations.append(
                HomeAssociation(
                    id=membership.association.id,
                    name=membership.association.name,
                    slug=membership.association.slug,
                    role=cast(Role, membership.role),
                    upcoming=planning.upcoming,
                    obsolete=planning.obsolete,
                    planning_period=planning.planning_period,
                )
            )
        return associations
