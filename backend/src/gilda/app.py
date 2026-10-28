from litestar import Litestar, Router

from gilda.db import create_database_plugin
from gilda.frontend import create_frontend_router, frontend_exception_handlers
from gilda.health.controllers import HealthController


def create_app() -> Litestar:
    api = Router(path="/api", route_handlers=[HealthController])
    frontend = create_frontend_router()
    return Litestar(
        route_handlers=[api] if frontend is None else [api, frontend],
        plugins=[create_database_plugin()],
        exception_handlers=frontend_exception_handlers(),
    )
