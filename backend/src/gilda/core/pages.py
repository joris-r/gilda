from typing import Any

import msgspec
from datastar_py.litestar import DatastarResponse, ServerSentEventGenerator
from litestar import Request, get, post
from litestar.di import NamedDependency
from litestar.exceptions import HTTPException, NotAuthorizedException, NotFoundException
from litestar.params import FromQuery
from litestar.response import Template
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import find_current_user, sign_in_as
from gilda.core.schemas import AccountCreate, NewPassword, PasswordResetRequest
from gilda.core.services import AccountService
from gilda.web.rendering import (
    fragment,
    interface_language,
    page,
    read_signals_dict,
    translate,
)

_SIGN_UP_REFUSALS = {
    403: "signUp.notInvited",
    409: "signUp.exists",
    503: "signUp.notSent",
}


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
                fragment(request, "form_error.html", message=message)
            )
        )
    sign_in_as(request, user)
    return DatastarResponse(ServerSentEventGenerator.redirect("/"))


@post("/sign-out", status_code=200)
async def sign_out(request: Request[Any, Any, Any]) -> DatastarResponse:
    request.clear_session()
    return DatastarResponse(ServerSentEventGenerator.redirect("/"))


def _form_error(request: Request[Any, Any, Any], key: str) -> DatastarResponse:
    message = translate(interface_language(request), key)
    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            fragment(request, "form_error.html", message=message)
        )
    )


@get("/signup")
async def sign_up_page(request: Request[Any, Any, Any]) -> Template:
    return page(request, "sign_up.html", message="")


@post("/signup", status_code=200)
async def sign_up(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> DatastarResponse:
    try:
        account = msgspec.convert(await read_signals_dict(request), AccountCreate)
    except msgspec.ValidationError:
        return _form_error(request, "error")
    try:
        await AccountService(db_session).create_account(
            account.display_name, account.email, account.password, interface_language(request)
        )
    except HTTPException as error:
        # This response succeeds, so the session would commit what the service has saved (R10).
        await db_session.rollback()
        return _form_error(request, _SIGN_UP_REFUSALS[error.status_code])
    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            fragment(request, "sign_up_done.html", email=account.email)
        )
    )


@post("/signup/resend", status_code=200)
async def resend_confirmation(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> DatastarResponse:
    signals = await read_signals_dict(request)
    await AccountService(db_session).resend_confirmation(
        str(signals.get("email", "")), interface_language(request)
    )
    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(fragment(request, "sign_up_resent.html"))
    )


@get("/verify-email")
async def verify_email_page(
    request: Request[Any, Any, Any], token: FromQuery[str] = ""
) -> Template:
    return page(request, "verify_email.html", token=token)


@post("/verify-email", status_code=200)
async def verify_email(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> DatastarResponse:
    signals = await read_signals_dict(request)
    try:
        user = await AccountService(db_session).confirm(str(signals.get("token", "")))
    except NotFoundException:
        return DatastarResponse(
            ServerSentEventGenerator.patch_elements(fragment(request, "verify_email_invalid.html"))
        )
    sign_in_as(request, user)
    return DatastarResponse(ServerSentEventGenerator.redirect("/"))


@get("/forgot-password")
async def forgot_password_page(request: Request[Any, Any, Any]) -> Template:
    return page(request, "forgot_password.html", message="")


@post("/forgot-password", status_code=200)
async def forgot_password(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> DatastarResponse:
    try:
        asked = msgspec.convert(await read_signals_dict(request), PasswordResetRequest)
    except msgspec.ValidationError:
        return _form_error(request, "error")
    await AccountService(db_session).request_password_reset(
        asked.email, interface_language(request)
    )
    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            fragment(request, "forgot_password_sent.html", email=asked.email)
        )
    )


@get("/reset-password")
async def reset_password_page(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    token: FromQuery[str] = "",
) -> Template:
    usable = await AccountService(db_session).reset_token_is_usable(token)
    return page(request, "reset_password.html", token=token, usable=usable, message="")


@post("/reset-password", status_code=200)
async def reset_password(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> DatastarResponse:
    signals = await read_signals_dict(request)
    try:
        new = msgspec.convert(signals, NewPassword)
    except msgspec.ValidationError:
        return _form_error(request, "error")
    try:
        user = await AccountService(db_session).reset_password(
            str(signals.get("token", "")), new.password
        )
    except NotFoundException:
        return DatastarResponse(
            ServerSentEventGenerator.patch_elements(
                fragment(request, "reset_password_invalid.html")
            )
        )
    sign_in_as(request, user)
    return DatastarResponse(ServerSentEventGenerator.redirect("/"))
