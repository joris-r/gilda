from datetime import date
from typing import Annotated
from uuid import UUID

from litestar import Controller, delete, get, patch, post
from litestar.di import NamedDependency, Provide
from litestar.params import FromPath, JSONBody, QueryParameter
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import provide_current_user
from gilda.core.models import User
from gilda.planning.schemas import (
    ClosureCreate,
    ClosureRead,
    RegistrationCreate,
    RegistrationRead,
    RegistrationUpdate,
    ScheduleRead,
    SlotCreate,
    SlotRead,
)
from gilda.planning.services import PlanningService


class PlanningController(Controller):
    path = "/associations/{association_id:uuid}"
    dependencies = {"current_user": Provide(provide_current_user)}  # noqa: RUF012

    @get("/slots")
    async def list_slots(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
    ) -> list[SlotRead]:
        return await PlanningService(db_session).list_slots(current_user, association_id)

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

    @delete("/slots/{slot_id:uuid}")
    async def delete_slot(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        slot_id: FromPath[UUID],
    ) -> None:
        await PlanningService(db_session).delete_slot(current_user, association_id, slot_id)

    @get("/closures")
    async def list_closures(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
    ) -> list[ClosureRead]:
        return await PlanningService(db_session).list_closures(current_user, association_id)

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

    @delete("/closures/{closure_id:uuid}")
    async def delete_closure(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        closure_id: FromPath[UUID],
    ) -> None:
        await PlanningService(db_session).delete_closure(current_user, association_id, closure_id)

    @get("/schedule")
    async def schedule(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        first: Annotated[date, QueryParameter(name="from")],
        last: Annotated[date, QueryParameter(name="to")],
    ) -> ScheduleRead:
        return await PlanningService(db_session).schedule(current_user, association_id, first, last)

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

    @patch("/registrations/{registration_id:uuid}")
    async def change_status(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
        registration_id: FromPath[UUID],
        data: JSONBody[RegistrationUpdate],
    ) -> RegistrationRead:
        return await PlanningService(db_session).change_status(
            current_user, association_id, registration_id, data.status
        )
