from uuid import UUID

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from sqlalchemy.dialects.postgresql import insert

from gilda.planning.models import (
    Absence,
    Closure,
    Note,
    PlanningPeriod,
    Preference,
    Registration,
    ShareLink,
    Slot,
)


class SlotRepository(SQLAlchemyAsyncRepository[Slot]):
    model_type = Slot


class ClosureRepository(SQLAlchemyAsyncRepository[Closure]):
    model_type = Closure


class PlanningPeriodRepository(SQLAlchemyAsyncRepository[PlanningPeriod]):
    model_type = PlanningPeriod


class RegistrationRepository(SQLAlchemyAsyncRepository[Registration]):
    model_type = Registration


class PreferenceRepository(SQLAlchemyAsyncRepository[Preference]):
    model_type = Preference

    async def set_value(self, slot_id: UUID, user_id: UUID, value: str) -> None:
        statement = (
            insert(Preference)
            .values(user_id=user_id, slot_id=slot_id, value=value)
            .on_conflict_do_update(index_elements=["user_id", "slot_id"], set_={"value": value})
        )
        await self.session.execute(statement)


class AbsenceRepository(SQLAlchemyAsyncRepository[Absence]):
    model_type = Absence


class NoteRepository(SQLAlchemyAsyncRepository[Note]):
    model_type = Note

    async def set_text(self, association_id: UUID, user_id: UUID, text: str) -> None:
        statement = (
            insert(Note)
            .values(association_id=association_id, user_id=user_id, text=text)
            .on_conflict_do_update(
                index_elements=["association_id", "user_id"], set_={"text": text}
            )
        )
        await self.session.execute(statement)


class ShareLinkRepository(SQLAlchemyAsyncRepository[ShareLink]):
    model_type = ShareLink
