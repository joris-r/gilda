from typing import Any

import msgspec
from datastar_py.litestar import DatastarResponse, ServerSentEventGenerator
from litestar import Request, get, post
from litestar.di import NamedDependency
from litestar.exceptions import (
    HTTPException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.params import FromQuery
from litestar.response import Template
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import SESSION_LINK_KEY, find_current_user, sign_in_as
from gilda.core.schemas import (
    AccessLinkRequest,
    AccountCreate,
    MemberCreate,
    MemberRead,
    NewPassword,
    PasswordResetRequest,
    Slug,
)
from gilda.core.services import (
    AccountService,
    AssociationService,
    ConflictException,
    MembershipEndHook,
)
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


@get("/association/new")
async def new_association_page(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    return page(request, "new_association.html", user=user, message="")


@post("/association/new", status_code=200)
async def create_association(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    signals = await read_signals_dict(request)
    name, slug = signals.get("name"), signals.get("slug")
    if not (name and isinstance(name, str) and slug and isinstance(slug, str)):
        return _form_error(request, "error")
    try:
        msgspec.convert(slug, Slug)
    except msgspec.ValidationError:
        return _form_error(request, "association.identifierInvalid")
    try:
        await AssociationService(db_session).create(user, name, slug)
    except ConflictException:
        return _form_error(request, "association.identifierTaken")
    return DatastarResponse(ServerSentEventGenerator.redirect(f"/association/{slug}"))


def _listed(members: list[MemberRead]) -> list[MemberRead]:
    """Managers first, then by display name."""
    return sorted(members, key=lambda m: (m.role != "manager", m.display_name.casefold()))


@get("/association/{slug:str}/members")
async def members_page(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
    except NotFoundException:
        return page(request, "association_unknown.html", user=user)
    return page(
        request,
        "members.html",
        user=user,
        association=association,
        members=_listed(association.members),
        message="",
    )


@post("/association/{slug:str}/members", status_code=200)
async def add_member(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    signals = await read_signals_dict(request)
    try:
        asked = msgspec.convert(
            {
                "display_name": signals.get("displayName"),
                "email": signals.get("email"),
                "role": signals.get("role"),
            },
            MemberCreate,
        )
    except msgspec.ValidationError:
        return _form_error(request, "error")
    associations = AssociationService(db_session)
    try:
        association = await associations.detail_by_slug(user, slug)
        added = await associations.add_member(
            user, association.id, asked.display_name, asked.email, asked.role
        )
    except ConflictException:
        return _form_error(request, "association.alreadyMember", name=asked.display_name)
    except (NotFoundException, PermissionDeniedException):
        return _form_error(request, "error")
    members = (await associations.detail(user, association.id)).members
    message = translate(interface_language(request), "association.added", name=added.display_name)
    return DatastarResponse(
        [
            ServerSentEventGenerator.patch_elements(
                fragment(request, "members_list.html", members=_listed(members))
            ),
            ServerSentEventGenerator.patch_elements(
                fragment(request, "notice.html", message=message)
            ),
            ServerSentEventGenerator.execute_script(
                "document.getElementById('add-member').close()"
            ),
        ]
    )


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


@post("/delete-account", status_code=200)
async def delete_account(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    membership_end_hooks: NamedDependency[list[MembershipEndHook]],
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is not None:
        await AccountService(db_session).delete_account(user, membership_end_hooks)
    request.clear_session()
    return DatastarResponse(ServerSentEventGenerator.redirect("/"))


@post("/revoke-access-link", status_code=200)
async def revoke_access_link(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is not None:
        await AccountService(db_session).revoke_link(user.id)
    if user is None or SESSION_LINK_KEY in request.session:
        request.clear_session()
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    message = translate(interface_language(request), "accessLink.revoked")
    return DatastarResponse(
        [
            ServerSentEventGenerator.patch_elements(
                fragment(request, "notice.html", message=message)
            ),
            ServerSentEventGenerator.execute_script(
                "document.getElementById('revoke-access-link').close()"
            ),
        ]
    )


def _form_error(request: Request[Any, Any, Any], key: str, **values: object) -> DatastarResponse:
    message = translate(interface_language(request), key, **values)
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


@get("/sign-in-link")
async def sign_in_link_page(request: Request[Any, Any, Any]) -> Template:
    return page(request, "sign_in_link.html", message="")


@post("/sign-in-link", status_code=200)
async def sign_in_link(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> DatastarResponse:
    try:
        asked = msgspec.convert(await read_signals_dict(request), AccessLinkRequest)
    except msgspec.ValidationError:
        return _form_error(request, "error")
    await AccountService(db_session).send_access_link(asked.email, interface_language(request))
    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            fragment(request, "sign_in_link_sent.html", email=asked.email)
        )
    )


@get("/access")
async def access_page(request: Request[Any, Any, Any], token: FromQuery[str] = "") -> Template:
    return page(request, "access.html", token=token)


@post("/access", status_code=200)
async def access(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession]
) -> DatastarResponse:
    signals = await read_signals_dict(request)
    try:
        user, link = await AccountService(db_session).sign_in_with_link(
            str(signals.get("token", ""))
        )
    except NotFoundException:
        return DatastarResponse(
            ServerSentEventGenerator.patch_elements(fragment(request, "access_invalid.html"))
        )
    sign_in_as(request, user, link)
    return DatastarResponse(ServerSentEventGenerator.redirect("/"))


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
