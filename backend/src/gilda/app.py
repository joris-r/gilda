from litestar import Litestar, Router
from litestar.di import Provide
from litestar.middleware import DefineMiddleware
from litestar.middleware.session import SessionMiddleware
from litestar.middleware.session.server_side import ServerSideSessionConfig

from gilda.core.controllers import AccountController, AssociationController
from gilda.core.models import UserSession
from gilda.core.services import MembershipEndHook
from gilda.core.sessions import SessionBackend
from gilda.db import create_database_config, create_database_plugin
from gilda.errors import api_exception_handlers
from gilda.frontend import create_frontend_router, frontend_exception_handlers
from gilda.home.controllers import HomeController
from gilda.planning.controllers import PlanningController, SharedScheduleController
from gilda.planning.services import end_membership as end_planning_membership


def membership_end_hooks() -> list[MembershipEndHook]:
    """What each domain does when a membership ends."""
    return [end_planning_membership]


def create_app() -> Litestar:
    database = create_database_config()
    sessions = SessionBackend(
        config=ServerSideSessionConfig(),
        alchemy_config=database,
        model=UserSession,
    )
    api = Router(
        path="/api",
        route_handlers=[
            AccountController,
            AssociationController,
            HomeController,
            PlanningController,
            SharedScheduleController,
        ],
        exception_handlers=api_exception_handlers(),
        dependencies={
            "membership_end_hooks": Provide(membership_end_hooks, sync_to_thread=False),
        },
    )
    frontend = create_frontend_router()
    return Litestar(
        route_handlers=[api] if frontend is None else [api, frontend],
        plugins=[create_database_plugin(database)],
        middleware=[DefineMiddleware(SessionMiddleware, backend=sessions)],
        exception_handlers=frontend_exception_handlers(),
    )
