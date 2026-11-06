from pathlib import Path
from types import ModuleType

from litestar import Litestar, Router
from litestar.di import Provide
from litestar.exceptions import MethodNotAllowedException, NotFoundException
from litestar.middleware import DefineMiddleware
from litestar.middleware.session import SessionMiddleware
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.plugins.jinja import JinjaTemplateEngine
from litestar.static_files import create_static_files_router
from litestar.template import TemplateConfig

from gilda import core, web
from gilda.core.controllers import AccountController, AssociationController
from gilda.core.models import UserSession
from gilda.core.pages import (
    delete_account,
    forgot_password,
    forgot_password_page,
    home,
    resend_confirmation,
    reset_password,
    reset_password_page,
    sign_in,
    sign_out,
    sign_up,
    sign_up_page,
    verify_email,
    verify_email_page,
)
from gilda.core.services import MembershipEndHook
from gilda.core.sessions import SessionBackend
from gilda.db import create_database_config, create_database_plugin
from gilda.errors import api_exception_handlers
from gilda.home.controllers import HomeController
from gilda.planning.controllers import PlanningController, SharedScheduleController
from gilda.planning.services import end_membership as end_planning_membership
from gilda.web.pages import choose_language, not_found


def membership_end_hooks() -> list[MembershipEndHook]:
    """What each domain does when a membership ends."""
    return [end_planning_membership]


def _directory_of(package: ModuleType) -> Path:
    return Path(package.__file__ or "").parent


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
    )
    static = create_static_files_router(path="/static", directories=[_directory_of(web) / "static"])
    return Litestar(
        route_handlers=[
            api,
            static,
            home,
            sign_in,
            sign_out,
            delete_account,
            forgot_password_page,
            forgot_password,
            reset_password_page,
            reset_password,
            sign_up_page,
            sign_up,
            resend_confirmation,
            verify_email_page,
            verify_email,
            choose_language,
        ],
        dependencies={
            "membership_end_hooks": Provide(membership_end_hooks, sync_to_thread=False),
        },
        exception_handlers={NotFoundException: not_found, MethodNotAllowedException: not_found},
        plugins=[create_database_plugin(database)],
        middleware=[DefineMiddleware(SessionMiddleware, backend=sessions)],
        template_config=TemplateConfig(
            directory=[_directory_of(web) / "templates", _directory_of(core) / "templates"],
            engine=JinjaTemplateEngine,
        ),
    )
