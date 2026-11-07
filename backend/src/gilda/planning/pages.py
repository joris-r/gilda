import re
from typing import Any
from uuid import UUID

import msgspec
from datastar_py.litestar import DatastarResponse, ServerSentEventGenerator
from litestar import Request, get, post
from litestar.di import NamedDependency
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.response import Template
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import find_current_user
from gilda.core.models import User
from gilda.core.schemas import AssociationDetail
from gilda.core.services import AssociationService, ConflictException
from gilda.planning.schemas import SlotCreate
from gilda.planning.services import PlanningService
from gilda.web.rendering import fragment, interface_language, page, read_signals_dict, translate

# A slot's action that fails on these shows the generic error.
_REFUSALS = (ClientException, NotFoundException, PermissionDeniedException)


@get("/association/{slug:str}/settings")
async def settings_page(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
    except NotFoundException:
        return page(request, "association_unknown.html", user=user)
    slots = await PlanningService(db_session).list_slots(user, association.id)
    return page(
        request, "settings.html", user=user, association=association, slots=slots, message=""
    )


def _error(request: Request[Any, Any, Any], error_id: str, key: str) -> DatastarResponse:
    """The message of a slot's dialog, which stays open."""
    message = translate(interface_language(request), key)
    return DatastarResponse(
        ServerSentEventGenerator.patch_elements(
            fragment(request, "form_error.html", message=message, error_id=error_id)
        )
    )


async def _slots_patched(
    request: Request[Any, Any, Any],
    db_session: AsyncSession,
    user: User,
    association: AssociationDetail,
    dialog: str,
    *more: Any,
) -> DatastarResponse:
    """Closes the dialog, then shows the slots as they now are."""
    slots = await PlanningService(db_session).list_slots(user, association.id)
    return DatastarResponse(
        [
            ServerSentEventGenerator.execute_script(f"document.getElementById('{dialog}').close()"),
            # On one line, so that each line of the list stays whole in the event.
            ServerSentEventGenerator.patch_elements(
                re.sub(
                    r"\s*\n\s*",
                    " ",
                    fragment(request, "settings_slots.html", association=association, slots=slots),
                )
            ),
            *more,
        ]
    )


def _asked(signals: dict[str, Any]) -> SlotCreate:
    return msgspec.convert({k: signals.get(k) for k in ("weekday", "start", "end")}, SlotCreate)


@post("/association/{slug:str}/settings/slots", status_code=200)
async def add_slot(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        asked = _asked(await read_signals_dict(request))
    except msgspec.ValidationError:
        return _error(request, "add-slot-error", "error")
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        added = await PlanningService(db_session).add_slot(
            user, association.id, asked.weekday, asked.start, asked.end
        )
    except ConflictException:
        return _error(request, "add-slot-error", "settings.slotExists")
    except _REFUSALS:
        return _error(request, "add-slot-error", "error")
    # R18: the next Add a slot opens from the slot just added.
    following = ServerSentEventGenerator.patch_signals(
        {"_nextWeekday": added.weekday, "_nextStart": added.end}
    )
    return await _slots_patched(request, db_session, user, association, "add-slot", following)


def _slot_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise NotFoundException("Slot not found.") from None


@post("/association/{slug:str}/settings/slots/{slot_id:str}/edit", status_code=200)
async def edit_slot(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    slot_id: str,
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "edit-slot-error"
    try:
        asked = _asked(await read_signals_dict(request))
    except msgspec.ValidationError:
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).edit_slot(
            user, association.id, _slot_id(slot_id), asked.weekday, asked.start, asked.end
        )
    except ConflictException:
        return _error(request, error_id, "settings.slotExists")
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _slots_patched(request, db_session, user, association, "edit-slot")


@post("/association/{slug:str}/settings/slots/{slot_id:str}/delete", status_code=200)
async def delete_slot(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    slot_id: str,
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).delete_slot(user, association.id, _slot_id(slot_id))
    except _REFUSALS:
        return _error(request, "delete-slot-error", "error")
    return await _slots_patched(request, db_session, user, association, "delete-slot")
