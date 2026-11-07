from typing import Any
from uuid import UUID

import msgspec
from datastar_py.litestar import DatastarResponse, ServerSentEventGenerator
from litestar import Request, get, post
from litestar.di import NamedDependency
from litestar.exceptions import (
    HTTPException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
    ServiceUnavailableException,
)
from litestar.params import FromQuery
from litestar.response import Template
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import SESSION_LINK_KEY, find_current_user, sign_in_as
from gilda.core.models import User
from gilda.core.schemas import (
    AccessLinkRequest,
    AccountCreate,
    AssociationDetail,
    MemberCreate,
    MemberRead,
    MemberUpdate,
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
    flash,
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


async def _members_list(
    request: Request[Any, Any, Any],
    associations: AssociationService,
    association: AssociationDetail,
) -> str:
    """The list of Members as it now is, with each member's dialogs."""
    return fragment(
        request,
        "members_list.html",
        association=association,
        members=_listed(association.members),
        with_link=await associations.with_access_link(association.members),
    )


@get("/association/{slug:str}/members")
async def members_page(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    associations = AssociationService(db_session)
    try:
        association = await associations.detail_by_slug(user, slug)
    except NotFoundException:
        return page(request, "association_unknown.html", user=user)
    return page(
        request,
        "members.html",
        user=user,
        association=association,
        members=_listed(association.members),
        with_link=await associations.with_access_link(association.members),
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
    now = await associations.detail(user, association.id)
    listed = await _members_list(request, associations, now)
    message = translate(interface_language(request), "association.added", name=added.display_name)
    return DatastarResponse(
        [
            ServerSentEventGenerator.patch_elements(listed),
            ServerSentEventGenerator.patch_elements(
                fragment(request, "notice.html", message=message)
            ),
            ServerSentEventGenerator.execute_script(
                "document.getElementById('add-member').close()"
            ),
        ]
    )


def _member(members: list[MemberRead], user_id: UUID) -> MemberRead:
    found = next((m for m in members if m.user_id == user_id), None)
    if found is None:
        raise NotFoundException("Not a member of this association.")
    return found


_CONFIRMATIONS = ("remove", "send-link", "revoke-link")


def _close(user_id: UUID, dialogs: tuple[str, ...]) -> str:
    """A script that closes these dialogs of the member, those still in the page."""
    return " ".join(f"document.getElementById('{d}-{user_id}')?.close();" for d in dialogs)


def _member_error(
    request: Request[Any, Any, Any], user_id: UUID, key: str, **values: object
) -> DatastarResponse:
    """The message of a member's edit dialog; a confirmation open over it closes."""
    message = translate(interface_language(request), key, **values)
    return DatastarResponse(
        [
            ServerSentEventGenerator.execute_script(_close(user_id, _CONFIRMATIONS)),
            ServerSentEventGenerator.patch_elements(
                fragment(
                    request, "form_error.html", message=message, error_id=f"edit-{user_id}-error"
                )
            ),
        ]
    )


async def _members_patched(
    request: Request[Any, Any, Any],
    associations: AssociationService,
    user: User,
    association_id: UUID,
    message: str,
    user_id: UUID,
) -> DatastarResponse:
    """Closes the member's dialogs, then shows the list as it now is, and the message."""
    association = await associations.detail(user, association_id)
    events = [
        ServerSentEventGenerator.execute_script(_close(user_id, (*_CONFIRMATIONS, "edit"))),
        ServerSentEventGenerator.patch_elements(
            await _members_list(request, associations, association)
        ),
        ServerSentEventGenerator.patch_elements(fragment(request, "notice.html", message=message)),
    ]
    if association.role != "manager":
        events.append(ServerSentEventGenerator.remove_elements("#members-toolbar"))
    return DatastarResponse(events)


@post("/association/{slug:str}/members/{user_id:uuid}/role", status_code=200)
async def change_role(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    user_id: UUID,
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    signals = await read_signals_dict(request)
    try:
        asked = msgspec.convert({"role": signals.get("role")}, MemberUpdate)
    except msgspec.ValidationError:
        return _member_error(request, user_id, "error")
    associations = AssociationService(db_session)
    try:
        association = await associations.detail_by_slug(user, slug)
        member = _member(association.members, user_id)
        if member.role == asked.role:
            return DatastarResponse(
                ServerSentEventGenerator.execute_script(
                    f"document.getElementById('edit-{user_id}').close()"
                )
            )
        await associations.change_role(user, association.id, user_id, asked.role)
    except ConflictException:
        return _member_error(request, user_id, "association.lastManager")
    except (NotFoundException, PermissionDeniedException):
        return _member_error(request, user_id, "error")
    language = interface_language(request)
    message = translate(
        language,
        "association.roleChanged",
        name=member.display_name,
        role=translate(language, f"roleNames.{asked.role}"),
    )
    return await _members_patched(request, associations, user, association.id, message, user_id)


@post("/association/{slug:str}/members/{user_id:uuid}/remove", status_code=200)
async def remove_member(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    membership_end_hooks: NamedDependency[list[MembershipEndHook]],
    slug: str,
    user_id: UUID,
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    associations = AssociationService(db_session)
    try:
        association = await associations.detail_by_slug(user, slug)
        member = _member(association.members, user_id)
        await associations.remove_member(user, association.id, user_id, membership_end_hooks)
    except ConflictException:
        return _member_error(request, user_id, "association.lastManager")
    except (NotFoundException, PermissionDeniedException):
        return _member_error(request, user_id, "error")
    if user_id == user.id:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    language = interface_language(request)
    message = translate(language, "association.removed", name=member.display_name)
    return await _members_patched(request, associations, user, association.id, message, user_id)


@post("/association/{slug:str}/members/{user_id:uuid}/send-link", status_code=200)
async def send_member_link(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    user_id: UUID,
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    language = interface_language(request)
    associations = AssociationService(db_session)
    try:
        association = await associations.detail_by_slug(user, slug)
        member = _member(association.members, user_id)
        await associations.send_member_link(user, association.id, user_id, language)
    except ServiceUnavailableException:
        return _member_error(request, user_id, "association.linkNotSent", name=member.display_name)
    except (NotFoundException, PermissionDeniedException):
        return _member_error(request, user_id, "error")
    message = translate(language, "association.linkSent", name=member.display_name)
    return await _members_patched(request, associations, user, association.id, message, user_id)


@post("/association/{slug:str}/members/{user_id:uuid}/revoke-link", status_code=200)
async def revoke_member_link(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    user_id: UUID,
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    associations = AssociationService(db_session)
    try:
        association = await associations.detail_by_slug(user, slug)
        member = _member(association.members, user_id)
        await associations.revoke_member_link(user, association.id, user_id)
    except (NotFoundException, PermissionDeniedException):
        return _member_error(request, user_id, "error")
    language = interface_language(request)
    message = translate(language, "association.linkRevoked", name=member.display_name)
    return await _members_patched(request, associations, user, association.id, message, user_id)


def _dialog_error(
    request: Request[Any, Any, Any], dialog: str, key: str, **values: object
) -> DatastarResponse:
    """The message of one of the association's dialogs on Members."""
    message = translate(interface_language(request), key, **values)
    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            fragment(request, "form_error.html", message=message, error_id=f"{dialog}-error")
        )
    )


def _closed(dialog: str) -> DatastarResponse:
    return DatastarResponse(
        ServerSentEventGenerator.execute_script(f"document.getElementById('{dialog}').close()")
    )


@post("/association/{slug:str}/rename", status_code=200)
async def rename_association(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    name = (await read_signals_dict(request)).get("name")
    if not (name and isinstance(name, str)):
        return _dialog_error(request, "rename", "error")
    associations = AssociationService(db_session)
    try:
        association = await associations.detail_by_slug(user, slug)
        if name == association.name:
            return _closed("rename")
        await associations.update(user, association.id, name, None)
    except (NotFoundException, PermissionDeniedException):
        return _dialog_error(request, "rename", "error")
    now = await associations.detail(user, association.id)
    message = translate(interface_language(request), "association.renamed", name=name)
    return DatastarResponse(
        [
            ServerSentEventGenerator.execute_script("document.getElementById('rename').close()"),
            ServerSentEventGenerator.patch_elements(
                fragment(request, "members_location.html", association=now)
            ),
            ServerSentEventGenerator.patch_elements(
                fragment(request, "association_actions.html", association=now)
            ),
            ServerSentEventGenerator.patch_elements(
                fragment(request, "notice.html", message=message)
            ),
        ]
    )


@post("/association/{slug:str}/identifier", status_code=200)
async def change_identifier(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    new_slug = (await read_signals_dict(request)).get("slug")
    if not (new_slug and isinstance(new_slug, str)):
        return _dialog_error(request, "identifier", "error")
    try:
        msgspec.convert(new_slug, Slug)
    except msgspec.ValidationError:
        return _dialog_error(request, "identifier", "association.identifierInvalid")
    associations = AssociationService(db_session)
    try:
        association = await associations.detail_by_slug(user, slug)
        if new_slug == association.slug:
            return _closed("identifier")
        await associations.update(user, association.id, None, new_slug)
    except ConflictException:
        return _dialog_error(request, "identifier", "association.identifierTaken")
    except (NotFoundException, PermissionDeniedException):
        return _dialog_error(request, "identifier", "error")
    language = interface_language(request)
    flash(request, translate(language, "association.identifierChanged", slug=new_slug))
    return DatastarResponse(ServerSentEventGenerator.redirect(f"/association/{new_slug}/members"))


@post("/association/{slug:str}/delete", status_code=200)
async def delete_association(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    associations = AssociationService(db_session)
    try:
        association = await associations.detail_by_slug(user, slug)
        await associations.delete(user, association.id)
    except (NotFoundException, PermissionDeniedException):
        # The page no longer matches what the user may do: show it as it now is.
        return DatastarResponse(ServerSentEventGenerator.redirect(f"/association/{slug}/members"))
    language = interface_language(request)
    flash(request, translate(language, "association.deleted", name=association.name))
    return DatastarResponse(ServerSentEventGenerator.redirect("/"))


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
