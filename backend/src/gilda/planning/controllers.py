from uuid import UUID

from litestar import Controller, post, put
from litestar.di import NamedDependency, Provide
from litestar.params import FromPath, JSONBody
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import provide_current_user
from gilda.core.models import User
from gilda.planning.schemas import (
    AbsenceCreate,
    AbsenceRead,
    ClosureCreate,
    ClosureRead,
    NoteData,
    PlanningPeriodData,
    RegistrationCreate,
    RegistrationRead,
    SlotCreate,
    SlotRead,
)
from gilda.planning.services import PlanningService


class PlanningController(Controller):
    path = "/associations/{association_id:uuid}"
    dependencies = {"current_user": Provide(provide_current_user)}  # noqa: RUF012

    @post("/slots")
    async def add_slot(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        data: JSONBody[SlotCreate],
    ) -> SlotRead:
        return await PlanningService(db_session).add_slot(
            current_user, association_id, data.weekday, data.start, data.end
        )

    @post("/closures")
    async def add_closure(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        data: JSONBody[ClosureCreate],
    ) -> ClosureRead:
        return await PlanningService(db_session).add_closure(
            current_user, association_id, data.first, data.last, data.label
        )

    @post("/absences")
    async def add_absence(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        data: JSONBody[AbsenceCreate],
    ) -> AbsenceRead:
        return await PlanningService(db_session).add_absence(
            current_user, association_id, data.first, data.last
        )

    @put("/note")
    async def set_note(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        data: JSONBody[NoteData],
    ) -> NoteData:
        return await PlanningService(db_session).set_note(current_user, association_id, data.text)

    @put("/planning-period")
    async def set_planning_period(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        data: JSONBody[PlanningPeriodData],
    ) -> PlanningPeriodData:
        return await PlanningService(db_session).set_planning_period(
            current_user, association_id, data.first, data.last
        )

    @post("/registrations")
    async def register(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        data: JSONBody[RegistrationCreate],
    ) -> RegistrationRead:
        return await PlanningService(db_session).register(
            current_user, association_id, data.user_id, data.date, data.start, data.end
        )
