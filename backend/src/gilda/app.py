from advanced_alchemy.extensions.litestar.session import SQLAlchemyAsyncSessionBackend
from litestar import Litestar, Router
from litestar.middleware import DefineMiddleware
from litestar.middleware.session import SessionMiddleware
from litestar.middleware.session.server_side import ServerSideSessionConfig

from gilda.core.controllers import AccountController, AssociationController
from gilda.core.models import UserSession
from gilda.db import create_database_config, create_database_plugin
from gilda.errors import api_exception_handlers
from gilda.frontend import create_frontend_router, frontend_exception_handlers


def create_app() -> Litestar:
    database = create_database_config()
    sessions = SQLAlchemyAsyncSessionBackend(
        config=ServerSideSessionConfig(),
        alchemy_config=database,
        model=UserSession,
    )
    api = Router(
        path="/api",
        route_handlers=[AccountController, AssociationController],
        exception_handlers=api_exception_handlers(),
    )
    frontend = create_frontend_router()
    return Litestar(
        route_handlers=[api] if frontend is None else [api, frontend],
        plugins=[create_database_plugin(database)],
        middleware=[DefineMiddleware(SessionMiddleware, backend=sessions)],
        exception_handlers=frontend_exception_handlers(),
    )
