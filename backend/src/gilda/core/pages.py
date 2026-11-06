from typing import Any

from datastar_py.litestar import DatastarResponse, ServerSentEventGenerator
from litestar import Request, get, post
from litestar.di import NamedDependency
from litestar.exceptions import NotAuthorizedException
from litestar.response import Template
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import find_current_user, sign_in_as
from gilda.core.services import AccountService
from gilda.web.rendering import (
    fragment,
    interface_language,
    page,
    read_signals_dict,
    translate,
)


@get("/")
async def home(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    return page(request, "home_temporary.html", user=user)


@post("/sign-in", status_code=200)
async def sign_in(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> DatastarResponse:
    signals = await read_signals_dict(request)
    try:
        user = await AccountService(db_session).authenticate(
            str(signals.get("email", "")), str(signals.get("password", ""))
        )
    except NotAuthorizedException:
        message = translate(interface_language(request), "signIn.wrong")
        return DatastarResponse(
            ServerSentEventGenerator.patch_elements(
                fragment(request, "sign_in_error.html", message=message)
            )
        )
    sign_in_as(request, user)
    return DatastarResponse(ServerSentEventGenerator.redirect("/"))


@post("/sign-out", status_code=200)
async def sign_out(request: Request[Any, Any, Any]) -> DatastarResponse:
    request.clear_session()
    return DatastarResponse(ServerSentEventGenerator.redirect("/"))
