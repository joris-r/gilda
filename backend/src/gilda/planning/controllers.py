from datetime import date
from typing import Annotated
from uuid import UUID

from litestar import Controller, delete, get, patch, post, put
from litestar.di import NamedDependency, Provide
from litestar.params import FromPath, JSONBody, QueryParameter
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import provide_current_user
from gilda.core.models import User
from gilda.planning.schemas import (
    AbsenceCreate,
    AbsenceRead,
    ClosureCreate,
    ClosureRead,
    MemberAbsenceRead,
    MemberNote,
    NoteData,
    PlanningPeriodData,
    RegistrationCount,
    RegistrationCreate,
    RegistrationRead,
    RegistrationUpdate,
    ScheduleRead,
    SharedAssociation,
    ShareLinkRead,
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

    @get("/registration-counts")
    async def registration_counts(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
    ) -> list[RegistrationCount] | None:
        return await PlanningService(db_session).registration_counts(current_user, association_id)

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

    @get("/member-absences")
    async def list_member_absences(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
    ) -> list[MemberAbsenceRead]:
        return await PlanningService(db_session).list_member_absences(current_user, association_id)

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

    @get("/notes")
    async def list_notes(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
    ) -> list[MemberNote]:
        return await PlanningService(db_session).list_notes(current_user, association_id)

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

    @get("/share-link")
    async def get_share_link(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
    ) -> ShareLinkRead | None:
        return await PlanningService(db_session).get_share_link(current_user, association_id)

    @post("/share-link")
    async def create_share_link(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
    ) -> ShareLinkRead:
        return await PlanningService(db_session).create_share_link(current_user, association_id)

    @delete("/share-link")
    async def revoke_share_link(
        self,
        current_user: NamedDependency[User],
        db_session: NamedDependency[AsyncSession],
        association_id: FromPath[UUID],
    ) -> None:
        await PlanningService(db_session).revoke_share_link(current_user, association_id)

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


class SharedScheduleController(Controller):
    """The Schedule read with a share link's token, signed in or not."""

    path = "/shared/{token:str}"

    @get()
    async def shared(
        self, db_session: NamedDependency[AsyncSession], token: FromPath[str]
    ) -> SharedAssociation:
        return await PlanningService(db_session).shared(token)

    @get("/schedule")
    async def schedule(
        self,
        db_session: NamedDependency[AsyncSession],
        token: FromPath[str],
        first: Annotated[date | None, QueryParameter(name="from")] = None,
        last: Annotated[date | None, QueryParameter(name="to")] = None,
    ) -> ScheduleRead:
        return await PlanningService(db_session).shared_schedule(token, first, last)
