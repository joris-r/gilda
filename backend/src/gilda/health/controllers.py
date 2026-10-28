from litestar import Controller, Response, get
from litestar.di import NamedDependency
from litestar.status_codes import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.health.schemas import HealthStatus
from gilda.health.services import database_is_reachable


class HealthController(Controller):
    path = "/health"

    @get()
    async def get_health(self, db_session: NamedDependency[AsyncSession]) -> Response[HealthStatus]:
        if await database_is_reachable(db_session):
            return Response(HealthStatus(api="ok", database="ok"), status_code=HTTP_200_OK)
        return Response(
            HealthStatus(api="ok", database="unreachable"),
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
        )
