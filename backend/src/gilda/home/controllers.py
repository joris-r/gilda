from litestar import Controller, get
from litestar.di import NamedDependency, Provide
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import provide_current_user
from gilda.core.models import User
from gilda.home.schemas import HomeAssociation
from gilda.home.services import HomeService


class HomeController(Controller):
    path = "/associations"
    dependencies = {"current_user": Provide(provide_current_user)}  # noqa: RUF012

    @get()
    async def list_associations(
        self, current_user: NamedDependency[User], db_session: NamedDependency[AsyncSession]
    ) -> list[HomeAssociation]:
        return await HomeService(db_session).list_for(current_user)
