from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from gilda.planning.models import Closure, PlanningPeriod, Preference, Registration, Slot


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
