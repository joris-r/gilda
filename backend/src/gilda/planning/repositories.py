from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from gilda.planning.models import Closure, PlanningPeriod, Registration, Slot


class SlotRepository(SQLAlchemyAsyncRepository[Slot]):
    model_type = Slot


class ClosureRepository(SQLAlchemyAsyncRepository[Closure]):
    model_type = Closure


class PlanningPeriodRepository(SQLAlchemyAsyncRepository[PlanningPeriod]):
    model_type = PlanningPeriod


class RegistrationRepository(SQLAlchemyAsyncRepository[Registration]):
    model_type = Registration
