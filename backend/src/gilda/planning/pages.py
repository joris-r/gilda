import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo

import msgspec
from datastar_py.litestar import DatastarResponse, ServerSentEventGenerator
from datastar_py.sse import DatastarEvent
from litestar import Request, get, post
from litestar.di import NamedDependency
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.params import FromPath
from litestar.response import Response, Template
from markupsafe import Markup, escape
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import Association, User
from gilda.core.pages import members_in_order
from gilda.core.schemas import AssociationDetail
from gilda.core.services import AssociationService, ConflictException
from gilda.core.sessions import find_current_user
from gilda.mailer import Language, site_url
from gilda.planning.schemas import (
    AbsenceCreate,
    AbsenceRead,
    ClosureCreate,
    ClosureRead,
    MemberFacts,
    PlanningPeriodData,
    PreferenceValue,
    ScheduleRead,
    SlotCreate,
    Status,
)
from gilda.planning.services import (
    AbsenceOrderException,
    AbsenceOverlapException,
    AbsencePastException,
    DateOrderException,
    DatePastException,
    PastException,
    PlanningService,
    TakenException,
    TimeOrderException,
)
from gilda.web.ordering import name_key
from gilda.web.rendering import (
    association_ref,
    format_day,
    fragment,
    interface_language,
    page,
    read_signals_dict,
    translate,
)

# An action that fails on these shows the generic error.
_REFUSALS = (ClientException, NotFoundException, PermissionDeniedException)
_ABSENCE_MESSAGES = {
    AbsenceOrderException: "availability.absenceOrder",
    AbsencePastException: "availability.absencePast",
    AbsenceOverlapException: "availability.absenceOverlap",
}
_ABSENCE_REFUSALS = tuple(_ABSENCE_MESSAGES)
_DATE_MESSAGES = {
    DateOrderException: "settings.dateOrder",
    DatePastException: "settings.datePast",
}
_DATE_REFUSALS = tuple(_DATE_MESSAGES)


@get("/association/{slug:str}/settings")
async def settings_page(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
    except NotFoundException:
        return page(request, "association_unknown.html", user=user)
    service = PlanningService(db_session)
    return page(
        request,
        "settings.html",
        user=user,
        association=association,
        period=await service.get_planning_period(user, association.id),
        closures=await service.list_closures(user, association.id),
        slots=await service.list_slots(user, association.id),
        members=members_in_order(association.members),
        values=await _all_preferences(service, user, association),
        link=await _share_link(service, user, association),
        message="",
    )


async def _all_preferences(
    service: PlanningService, user: User, association: AssociationDetail
) -> dict[tuple[UUID, UUID], str]:
    """Each member's preference on each slot that has one, for Members' preferences."""
    if association.role != "manager":
        return {}
    preferences = await service.list_preferences(user, association.id)
    return {(p.user_id, p.slot_id): p.value for p in preferences}


def _one_line(shown: str) -> str:
    """On one line, so that each line of a list stays whole in the event."""
    return re.sub(r"\s*\n\s*", " ", shown)


def _error(request: Request[Any, Any, Any], error_id: str, key: str) -> DatastarResponse:
    """The message of a dialog, which stays open."""
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
    """Closes the dialog, then shows the slots, and the columns of Members' preferences, as they
    now are."""
    service = PlanningService(db_session)
    slots = await service.list_slots(user, association.id)
    shown = fragment(request, "settings_slots.html", association=association, slots=slots)
    grid = fragment(
        request,
        "settings_preferences.html",
        association=association,
        slots=slots,
        members=members_in_order(association.members),
        values=await _all_preferences(service, user, association),
    )
    return _patched(dialog, shown, ServerSentEventGenerator.patch_elements(_one_line(grid)), *more)


def _patched(dialog: str, shown: str, *more: Any) -> DatastarResponse:
    """Closes the dialog, then puts `shown` in place of the part of the page it stands for."""
    return DatastarResponse(
        [
            ServerSentEventGenerator.execute_script(f"document.getElementById('{dialog}').close()"),
            ServerSentEventGenerator.patch_elements(_one_line(shown)),
            *more,
        ]
    )


def _asked(signals: dict[str, Any]) -> SlotCreate:
    return msgspec.convert({k: signals.get(k) for k in ("weekday", "start", "end")}, SlotCreate)


@post("/association/{slug:str}/settings/slots", status_code=200)
async def add_slot(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        asked = _asked(await read_signals_dict(request))
    except msgspec.ValidationError:
        return _error(request, "add-slot-error", "error")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        added = await PlanningService(db_session).add_slot(
            user, association.id, asked.weekday, asked.start, asked.end
        )
    except TimeOrderException:
        return _error(request, "add-slot-error", "settings.timeOrder")
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
    slug: FromPath[str],
    slot_id: FromPath[str],
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
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await PlanningService(db_session).edit_slot(
            user, association.id, _slot_id(slot_id), asked.weekday, asked.start, asked.end
        )
    except TimeOrderException:
        return _error(request, error_id, "settings.timeOrder")
    except ConflictException:
        return _error(request, error_id, "settings.slotExists")
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _slots_patched(request, db_session, user, association, "edit-slot")


@post("/association/{slug:str}/settings/slots/{slot_id:str}/delete", status_code=200)
async def delete_slot(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: FromPath[str],
    slot_id: FromPath[str],
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await PlanningService(db_session).delete_slot(user, association.id, _slot_id(slot_id))
    except _REFUSALS:
        return _error(request, "delete-slot-error", "error")
    return await _slots_patched(request, db_session, user, association, "delete-slot")


# Members' preferences


@get("/association/{slug:str}/settings/preferences")
async def members_preferences(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> Response[str]:
    """Members' preferences as they now are, for the screen shown again after being hidden: 401
    when signed out, 404 or 403 when the user no longer manages the association."""
    user = await find_current_user(request, db_session)
    if user is None:
        return Response("", status_code=401)
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
    except NotFoundException:
        return Response("", status_code=404)
    if association.role != "manager":
        return Response("", status_code=403)
    service = PlanningService(db_session)
    shown = fragment(
        request,
        "settings_preferences.html",
        association=association,
        slots=await service.list_slots(user, association.id),
        members=members_in_order(association.members),
        values=await _all_preferences(service, user, association),
    )
    return Response(shown, media_type="text/html")


@post("/association/{slug:str}/settings/preferences/{slot_id:str}/{user_id:str}", status_code=200)
async def choose_member_preference(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: FromPath[str],
    slot_id: FromPath[str],
    user_id: FromPath[str],
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "members-preferences-error"
    value = (await read_signals_dict(request)).get("value")
    if value not in ("", "preferred", "possible", "unavailable"):
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        if association.role != "manager":
            raise PermissionDeniedException("Only managers set the members' preferences.")
        service = PlanningService(db_session)
        wanted = _slot_id(slot_id)
        slots = await service.list_slots(user, association.id)
        slot = next((s for s in slots if s.id == wanted), None)
        member = next((m for m in association.members if str(m.user_id) == user_id), None)
        if slot is None or member is None:
            raise NotFoundException("Slot or member not found.")
        if value:
            await service.set_preference(
                user, association.id, slot.id, member.user_id, cast("PreferenceValue", value)
            )
        else:
            await service.delete_preference(user, association.id, slot.id, member.user_id)
    except _REFUSALS:
        return _error(request, error_id, "error")
    return DatastarResponse(
        [
            ServerSentEventGenerator.execute_script(
                f"gildaPreferenceSaved('member-preference-{member.user_id}-{slot.id}', '{value}')"
            ),
            ServerSentEventGenerator.patch_elements(
                fragment(request, "form_error.html", message="", error_id=error_id)
            ),
        ]
    )


# Planning period


async def _period_patched(
    request: Request[Any, Any, Any],
    db_session: AsyncSession,
    user: User,
    association: AssociationDetail,
    dialog: str,
) -> DatastarResponse:
    """Closes the dialog, then shows the period as it now is."""
    period = await PlanningService(db_session).get_planning_period(user, association.id)
    shown = fragment(request, "settings_period.html", association=association, period=period)
    return _patched(dialog, shown)


@post("/association/{slug:str}/settings/period", status_code=200)
async def set_period(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "edit-period-error"
    signals = await read_signals_dict(request)
    try:
        asked = msgspec.convert({k: signals.get(k) for k in ("first", "last")}, PlanningPeriodData)
    except msgspec.ValidationError:
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await PlanningService(db_session).set_planning_period(
            user, association.id, asked.first, asked.last
        )
    except DateOrderException:
        return _error(request, error_id, "settings.dateOrder")
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _period_patched(request, db_session, user, association, "edit-period")


@post("/association/{slug:str}/settings/period/clear", status_code=200)
async def clear_period(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await PlanningService(db_session).clear_planning_period(user, association.id)
    except _REFUSALS:
        return _error(request, "clear-period-error", "error")
    return await _period_patched(request, db_session, user, association, "clear-period")


# Closures


async def _closures_patched(
    request: Request[Any, Any, Any],
    db_session: AsyncSession,
    user: User,
    association: AssociationDetail,
    dialog: str,
) -> DatastarResponse:
    """Closes the dialog, then shows the closures as they now are."""
    closures = await PlanningService(db_session).list_closures(user, association.id)
    shown = fragment(request, "settings_closures.html", association=association, closures=closures)
    return _patched(dialog, shown)


def _asked_closure(signals: dict[str, Any]) -> ClosureCreate:
    """The closure of a dialog; an empty Label means none."""
    asked = msgspec.convert({k: signals.get(k) for k in ("first", "last")}, ClosureCreate)
    label = signals.get("label")
    if label is not None and not isinstance(label, str):
        raise msgspec.ValidationError("The label must be text.")
    asked.label = (label or "").strip() or None
    return asked


def _closure_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise NotFoundException("Closure not found.") from None


@post("/association/{slug:str}/settings/closures", status_code=200)
async def add_closure(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "add-closure-error"
    try:
        asked = _asked_closure(await read_signals_dict(request))
    except msgspec.ValidationError:
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await PlanningService(db_session).add_closure(
            user, association.id, asked.first, asked.last, asked.label
        )
    except _DATE_REFUSALS as refusal:
        return _error(request, error_id, _DATE_MESSAGES[type(refusal)])
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _closures_patched(request, db_session, user, association, "add-closure")


@post("/association/{slug:str}/settings/closures/{closure_id:str}/edit", status_code=200)
async def edit_closure(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: FromPath[str],
    closure_id: FromPath[str],
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "edit-closure-error"
    try:
        asked = _asked_closure(await read_signals_dict(request))
    except msgspec.ValidationError:
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await PlanningService(db_session).edit_closure(
            user, association.id, _closure_id(closure_id), asked.first, asked.last, asked.label
        )
    except _DATE_REFUSALS as refusal:
        return _error(request, error_id, _DATE_MESSAGES[type(refusal)])
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _closures_patched(request, db_session, user, association, "edit-closure")


@post("/association/{slug:str}/settings/closures/{closure_id:str}/delete", status_code=200)
async def delete_closure(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: FromPath[str],
    closure_id: FromPath[str],
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await PlanningService(db_session).delete_closure(
            user, association.id, _closure_id(closure_id)
        )
    except _REFUSALS:
        return _error(request, "delete-closure-error", "error")
    return await _closures_patched(request, db_session, user, association, "delete-closure")


# My availability


# Share link


async def _share_link(service: PlanningService, user: User, association: AssociationDetail) -> str:
    """The URL of the association's share link for Share link, empty when there is none or the
    user is no manager."""
    if association.role != "manager":
        return ""
    token = await service.get_share_link(user, association.id)
    return "" if token is None else site_url(f"/shared/{token}")


_CLOSE_SHARE_LINK_DIALOGS = (
    "document.getElementById('replace-share-link')?.close();"
    " document.getElementById('revoke-share-link')?.close()"
)


async def _share_link_patched(
    request: Request[Any, Any, Any],
    service: PlanningService,
    user: User,
    association: AssociationDetail,
) -> DatastarResponse:
    """Closes the confirmations, then shows the Share link section as it now is."""
    link = await _share_link(service, user, association)
    shown = fragment(request, "settings_share_link_line.html", association=association, link=link)
    return _patched_by(_CLOSE_SHARE_LINK_DIALOGS, shown)


def _patched_by(script: str, shown: str) -> DatastarResponse:
    return DatastarResponse(
        [
            ServerSentEventGenerator.execute_script(script),
            ServerSentEventGenerator.patch_elements(_one_line(shown)),
        ]
    )


@post("/association/{slug:str}/settings/share-link", status_code=200)
async def create_share_link(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    service = PlanningService(db_session)
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await service.create_share_link(user, association.id)
    except _REFUSALS:
        return _error(request, "share-link-error", "error")
    return await _share_link_patched(request, service, user, association)


@post("/association/{slug:str}/settings/share-link/revoke", status_code=200)
async def revoke_share_link(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    service = PlanningService(db_session)
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await service.revoke_share_link(user, association.id)
    except _REFUSALS:
        return _error(request, "share-link-error", "error")
    return await _share_link_patched(request, service, user, association)


async def _own_preferences(
    service: PlanningService, user: User, association_id: UUID
) -> dict[UUID, str]:
    """The user's own preference on each slot that has one."""
    preferences = await service.list_preferences(user, association_id)
    return {p.slot_id: p.value for p in preferences if p.user_id == user.id}


@get("/association/{slug:str}/availability")
async def availability_page(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
    except NotFoundException:
        return page(request, "association_unknown.html", user=user)
    service = PlanningService(db_session)
    return page(
        request,
        "availability.html",
        user=user,
        association=association,
        slots=await service.list_slots(user, association.id),
        values=await _own_preferences(service, user, association.id),
        absences=await _upcoming_absences(service, user, association),
        note=(await service.get_note(user, association.id)).text,
    )


@post("/association/{slug:str}/availability/preferences/{slot_id:str}", status_code=200)
async def choose_preference(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: FromPath[str],
    slot_id: FromPath[str],
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "preferences-error"
    value = (await read_signals_dict(request)).get("value")
    if value not in ("", "preferred", "possible", "unavailable"):
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        service = PlanningService(db_session)
        wanted = _slot_id(slot_id)
        slots = await service.list_slots(user, association.id)
        slot = next((s for s in slots if s.id == wanted), None)
        if slot is None:
            raise NotFoundException("Slot not found.")
        if value:
            await service.set_preference(
                user, association.id, slot.id, user.id, cast("PreferenceValue", value)
            )
        else:
            await service.delete_preference(user, association.id, slot.id, user.id)
    except _REFUSALS:
        return _error(request, error_id, "error")
    return DatastarResponse(
        [
            ServerSentEventGenerator.execute_script(
                f"gildaPreferenceSaved('preference-{slot.id}', '{value}')"
            ),
            ServerSentEventGenerator.patch_elements(
                fragment(request, "form_error.html", message="", error_id=error_id)
            ),
        ]
    )


# My availability: Absences


async def _upcoming_absences(
    service: PlanningService, user: User, association: AssociationDetail
) -> list[AbsenceRead]:
    """The user's own absences, from those ending today on, by first date."""
    today = datetime.now(ZoneInfo(association.timezone)).date()
    absences = await service.list_absences(user, association.id)
    return [a for a in absences if a.last >= today]


async def _absences_patched(
    request: Request[Any, Any, Any],
    db_session: AsyncSession,
    user: User,
    association: AssociationDetail,
    dialog: str,
) -> DatastarResponse:
    """Closes the dialog, then shows the absences as they now are."""
    absences = await _upcoming_absences(PlanningService(db_session), user, association)
    return _patched(dialog, fragment(request, "availability_absences.html", absences=absences))


def _asked_absence(signals: dict[str, Any]) -> AbsenceCreate:
    return msgspec.convert({k: signals.get(k) for k in ("first", "last")}, AbsenceCreate)


def _absence_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise NotFoundException("Absence not found.") from None


@post("/association/{slug:str}/availability/absences", status_code=200)
async def add_absence(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "add-absence-error"
    try:
        asked = _asked_absence(await read_signals_dict(request))
    except msgspec.ValidationError:
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await PlanningService(db_session).add_absence(user, association.id, asked.first, asked.last)
    except _ABSENCE_REFUSALS as refusal:
        return _error(request, error_id, _ABSENCE_MESSAGES[type(refusal)])
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _absences_patched(request, db_session, user, association, "add-absence")


@post("/association/{slug:str}/availability/absences/{absence_id:str}/edit", status_code=200)
async def edit_absence(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: FromPath[str],
    absence_id: FromPath[str],
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "edit-absence-error"
    try:
        asked = _asked_absence(await read_signals_dict(request))
    except msgspec.ValidationError:
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await PlanningService(db_session).edit_absence(
            user, association.id, _absence_id(absence_id), asked.first, asked.last
        )
    except _ABSENCE_REFUSALS as refusal:
        return _error(request, error_id, _ABSENCE_MESSAGES[type(refusal)])
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _absences_patched(request, db_session, user, association, "edit-absence")


@post("/association/{slug:str}/availability/absences/{absence_id:str}/delete", status_code=200)
async def delete_absence(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: FromPath[str],
    absence_id: FromPath[str],
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        await PlanningService(db_session).delete_absence(
            user, association.id, _absence_id(absence_id)
        )
    except _REFUSALS:
        return _error(request, "delete-absence-error", "error")
    return await _absences_patched(request, db_session, user, association, "delete-absence")


# My availability: Note for the managers


@post("/association/{slug:str}/availability/note", status_code=200)
async def save_note(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "edit-note-error"
    text = (await read_signals_dict(request)).get("text")
    if not isinstance(text, str):
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        saved = await PlanningService(db_session).set_note(user, association.id, text)
    except _REFUSALS:
        return _error(request, error_id, "error")
    text = saved.text
    shown = fragment(request, "availability_note.html", note=text)
    # The note's lines are <br> in `shown`, so putting it on one line keeps them.
    return _patched("edit-note", shown, ServerSentEventGenerator.patch_signals({"_note": text}))


# Schedule

# "More weeks" adds this many weeks.
_MORE_WEEKS = 4
# "More weeks" refuses a range longer than this, which would take long to build.
_MAX_WEEKS = 520


@dataclass
class _Item:
    """An occurrence, or an obsolete registration placed like one."""

    date: date
    start: str
    end: str
    name: str | None
    status: str
    obsolete: bool
    lane: int = 0
    lanes: int = 1
    top: float = 0
    bottom: float = 0

    @property
    def times(self) -> str:
        return f"{_short_clock(self.start)}–{_short_clock(self.end)}"  # noqa: RUF001


@dataclass
class _Day:
    date: date
    items: list[_Item]
    closures: list[ClosureRead]
    past: bool
    within: bool
    after: bool

    @property
    def lanes(self) -> int:
        return max([1, *(item.lanes for item in self.items)])

    @property
    def closed(self) -> bool:
        return bool(self.closures)

    @property
    def closure_labels(self) -> list[str]:
        """The labels of the closures covering the day, by first date, each once."""
        ordered = sorted(self.closures, key=lambda closure: closure.first)
        return list(dict.fromkeys(c.label for c in ordered if c.label))


@dataclass
class _Week:
    monday: date
    days: list[_Day]
    today: bool = False
    starts: bool = False
    ends: bool = False

    @property
    def number(self) -> int:
        return self.monday.isocalendar().week


@dataclass
class _Weeks:
    """What the weeks of the Schedule show, from `first`, a Monday, to `last`, a Sunday."""

    first: date
    last: date
    today: date
    period: PlanningPeriodData | None
    weeks: list[_Week] = field(default_factory=list)
    columns: int = 0
    first_hour: int = 0
    hours: int = 1
    empty: bool = True

    @property
    def ticks(self) -> list[dict[str, Any]]:
        return [
            {
                "hour": self.first_hour + n,
                "p": round(n / self.hours, 4),
                "minor": self.hours > 6 and n % 2 == 1,
            }
            for n in range(self.hours + 1)
        ]


def _minutes(clock: str) -> int:
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


def _short_clock(clock: str) -> str:
    """A time as the Schedule names it, e.g. "10" for 10:00 and "10:30"."""
    hours, minutes = clock.split(":")
    return str(int(hours)) if minutes == "00" else f"{int(hours)}:{minutes}"


def _with_lanes(items: list[_Item]) -> list[_Item]:
    """A day's items by start, each in a lane, so that those that overlap sit side by side."""
    items.sort(key=lambda item: (_minutes(item.start), _minutes(item.end)))
    cluster: list[_Item] = []
    cluster_end = 0
    lane_ends: list[int] = []
    for item in [*items, None]:
        if item is None or _minutes(item.start) >= cluster_end:
            for member in cluster:
                member.lanes = len(lane_ends)
            cluster, lane_ends = [], []
            if item is None:
                break
        free = [n for n, lane_end in enumerate(lane_ends) if lane_end <= _minutes(item.start)]
        if free:
            item.lane = free[0]
            lane_ends[item.lane] = _minutes(item.end)
        else:
            item.lane = len(lane_ends)
            lane_ends.append(_minutes(item.end))
        cluster.append(item)
        cluster_end = max(cluster_end, _minutes(item.end))
    return items


def _weeks_view(schedule: ScheduleRead, period: PlanningPeriodData | None, today: date) -> _Weeks:
    first = schedule.from_ - timedelta(days=schedule.from_.weekday())
    last = schedule.to + timedelta(days=6 - schedule.to.weekday())
    view = _Weeks(first=first, last=last, today=today, period=period)
    by_date: dict[date, list[_Item]] = {}
    for occurrence in schedule.occurrences:
        registration = occurrence.registration
        by_date.setdefault(occurrence.date, []).append(
            _Item(
                date=occurrence.date,
                start=occurrence.start,
                end=occurrence.end,
                name=registration.display_name if registration else None,
                status=registration.status if registration else "free",
                obsolete=False,
            )
        )
    for obsolete in schedule.obsolete:
        by_date.setdefault(obsolete.date, []).append(
            _Item(
                date=obsolete.date,
                start=obsolete.start,
                end=obsolete.end,
                name=obsolete.display_name,
                status=obsolete.status,
                obsolete=True,
            )
        )
    items = [item for day in by_date.values() for item in _with_lanes(day)]
    view.empty = not items
    if items:
        view.first_hour = min(_minutes(item.start) for item in items) // 60
        last_hour = math.ceil(max(_minutes(item.end) for item in items) / 60)
        view.hours = max(1, last_hour - view.first_hour)
        span = view.hours * 60
        for item in items:
            item.top = round((_minutes(item.start) - view.first_hour * 60) / span, 4)
            item.bottom = round((_minutes(item.end) - view.first_hour * 60) / span, 4)
    closed = set(schedule.closed_days)
    columns = sorted({item.date.weekday() for item in items} | {day.weekday() for day in closed})
    view.columns = len(columns)
    monday = first
    while monday <= last:
        # With no occurrence, only the weeks that hold a closed day show.
        if view.empty and not any(monday <= day <= monday + timedelta(days=6) for day in closed):
            monday += timedelta(weeks=1)
            continue
        days = []
        for column in columns:
            day = monday + timedelta(days=column)
            days.append(
                _Day(
                    date=day,
                    items=by_date.get(day, []),
                    closures=[c for c in schedule.closures if c.first <= day <= c.last],
                    past=day < today,
                    within=period is not None and period.first <= day <= period.last,
                    after=period is not None and day > period.last,
                )
            )
        sunday = monday + timedelta(days=6)
        view.weeks.append(
            _Week(
                monday=monday,
                days=days,
                today=monday <= today <= sunday,
                starts=period is not None and monday <= period.first <= sunday,
                ends=period is not None and monday <= period.last <= sunday,
            )
        )
        monday += timedelta(weeks=1)
    return view


def _today(association: AssociationDetail | Association) -> date:
    return datetime.now(ZoneInfo(association.timezone)).date()


@get("/association/{slug:str}")
async def schedule_page(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    try:
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
    except NotFoundException:
        return page(request, "association_unknown.html", user=user)
    service = PlanningService(db_session)
    schedule = await service.schedule(user, association.id, None, None)
    period = await service.get_planning_period(user, association.id)
    return page(
        request,
        "schedule.html",
        user=user,
        association=association,
        view=_weeks_view(schedule, period, _today(association)),
    )


def _shown_range(signals: dict[str, Any]) -> tuple[date, date]:
    """The weeks the Schedule shows, from their first Monday to their last Sunday."""
    first, last = signals.get("from"), signals.get("to")
    if not isinstance(first, str) or not isinstance(last, str):
        raise ClientException("Give the weeks shown.")
    try:
        first_day, last_day = date.fromisoformat(first), date.fromisoformat(last)
    except ValueError as error:
        raise ClientException("Give the weeks shown as dates.") from error
    if last_day < first_day or (last_day - first_day).days > _MAX_WEEKS * 7:
        raise ClientException("Give a range of weeks.")
    return first_day, last_day


@post("/association/{slug:str}/weeks", status_code=200)
async def more_weeks(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "weeks-error"
    try:
        first, last = _shown_range(await read_signals_dict(request))
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        service = PlanningService(db_session)
        first -= timedelta(days=first.weekday())
        last += timedelta(days=6 - last.weekday(), weeks=_MORE_WEEKS)
        schedule = await service.schedule(user, association.id, first, last)
        period = await service.get_planning_period(user, association.id)
    except _REFUSALS:
        return _error(request, error_id, "error")
    shown = fragment(
        request,
        "schedule_weeks.html",
        association=association,
        view=_weeks_view(schedule, period, _today(association)),
    )
    return DatastarResponse(ServerSentEventGenerator.patch_elements(_one_line(shown)))


def _query_range(request: Request[Any, Any, Any]) -> dict[str, Any]:
    return {key: request.query_params.get(key) for key in ("from", "to")}


@get("/association/{slug:str}/weeks-again")
async def weeks_again(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> Response[str]:
    """The weeks from `from` to `to` as they now are, for a Schedule shown again once today
    changes: 401 when signed out, any other failure a plain status."""
    user = await find_current_user(request, db_session)
    if user is None:
        return Response("", status_code=401)
    try:
        first, last = _shown_range(_query_range(request))
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        service = PlanningService(db_session)
        schedule = await service.schedule(user, association.id, first, last)
        period = await service.get_planning_period(user, association.id)
    except NotFoundException:
        return Response("", status_code=404)
    except PermissionDeniedException:
        return Response("", status_code=403)
    except ClientException:
        return Response("", status_code=400)
    shown = fragment(
        request,
        "schedule_weeks.html",
        association=association,
        view=_weeks_view(schedule, period, _today(association)),
    )
    return Response(shown, media_type="text/html")


# Shared schedule, read with a share link's token, signed in or not.


@get("/shared/{token:str}")
async def shared_schedule_page(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], token: FromPath[str]
) -> Template:
    try:
        association, schedule, period = await PlanningService(db_session).shared(token, None, None)
    except NotFoundException:
        return page(request, "shared_invalid.html")
    return page(
        request,
        "shared_schedule.html",
        association=association,
        token=token,
        view=_weeks_view(schedule, period, _today(association)),
    )


def _gone(request: Request[Any, Any, Any]) -> DatastarResponse:
    """The Shared schedule of a link that is no longer valid, as that link opens."""
    shown = fragment(request, "shared_gone.html")
    return DatastarResponse(
        [
            ServerSentEventGenerator.patch_elements(_one_line(shown)),
            ServerSentEventGenerator.execute_script("window.location.reload()"),
        ]
    )


@get("/shared/{token:str}/weeks-again")
async def shared_weeks_again(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], token: FromPath[str]
) -> Response[str]:
    """The weeks from `from` to `to` as they now are, for a Shared schedule shown again once
    today changes: 404 when the link is no longer valid, any other failure a plain status."""
    try:
        first, last = _shown_range(_query_range(request))
        association, schedule, period = await PlanningService(db_session).shared(token, first, last)
    except NotFoundException:
        return Response("", status_code=404)
    except ClientException:
        return Response("", status_code=400)
    shown = fragment(
        request,
        "schedule_weeks.html",
        association=association,
        shared=token,
        view=_weeks_view(schedule, period, _today(association)),
    )
    return Response(shown, media_type="text/html")


@post("/shared/{token:str}/weeks", status_code=200)
async def shared_more_weeks(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], token: FromPath[str]
) -> DatastarResponse:
    try:
        first, last = _shown_range(await read_signals_dict(request))
        first -= timedelta(days=first.weekday())
        last += timedelta(days=6 - last.weekday(), weeks=_MORE_WEEKS)
        association, schedule, period = await PlanningService(db_session).shared(token, first, last)
    except NotFoundException:
        return _gone(request)
    except _REFUSALS:
        return _error(request, "weeks-error", "error")
    shown = fragment(
        request,
        "schedule_weeks.html",
        association=association,
        shared=token,
        view=_weeks_view(schedule, period, _today(association)),
    )
    return DatastarResponse(ServerSentEventGenerator.patch_elements(_one_line(shown)))


# The Schedule's menu, opened on an occurrence or an obsolete registration.

_CLOCK = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@dataclass
class _Name:
    """A member's display name in the manager's menu, which proposes the occurrence to them."""

    user_id: UUID
    name: str
    count: int | None
    preference: PreferenceValue | None
    # The text of the absence icon, or "" when the member is not absent.
    absence: str
    # The text of the note icon, as an attribute value that keeps the note's lines, or "".
    note: Markup

    @property
    def look(self) -> str:
        if self.absence:
            return "absent"
        return f"preference-{self.preference}" if self.preference else ""


@dataclass
class _Menu:
    """What the menu of an occurrence or an obsolete registration offers the user."""

    date: date
    start: str
    end: str
    registration_id: UUID | None = None
    sign_up: bool = False
    confirm: bool = False
    cancel: bool = False
    # A volunteer may take over the registration of another member.
    take_over: bool = False
    # The member whose registration the occurrence holds, when it is not cancelled.
    taken_by: UUID | None = None
    taken_by_name: str = ""
    names: list[_Name] = field(default_factory=list)

    @property
    def times(self) -> str:
        return f"{_short_clock(self.start)}–{_short_clock(self.end)}"  # noqa: RUF001


def _asked_occurrence(signals: dict[str, Any]) -> tuple[date, str, str]:
    day, start, end = signals.get("date"), signals.get("start"), signals.get("end")
    if not all(isinstance(value, str) for value in (day, start, end)):
        raise ClientException("Give the occurrence's date, start and end.")
    if not _CLOCK.match(cast(str, start)) or not _CLOCK.match(cast(str, end)):
        raise ClientException("Give the occurrence's times as HH:MM.")
    try:
        return date.fromisoformat(cast(str, day)), cast(str, start), cast(str, end)
    except ValueError as error:
        raise ClientException("Give the occurrence's date as a date.") from error


def _menu_of(schedule: ScheduleRead, user: User, manages: bool, asked: _Menu) -> _Menu:
    """The menu of the occurrence or obsolete registration `asked` names, without its names."""
    for occurrence in schedule.occurrences:
        if (occurrence.start, occurrence.end) != (asked.start, asked.end):
            continue
        registration = occurrence.registration
        if registration is None or registration.status == "cancelled":
            asked.sign_up = True
            return asked
        allowed = manages or registration.user_id == user.id
        asked.taken_by = registration.user_id
        asked.registration_id = registration.id
        asked.confirm = allowed and registration.status == "proposed"
        asked.cancel = allowed
        asked.take_over = not allowed
        return asked
    for obsolete in schedule.obsolete:
        if (obsolete.start, obsolete.end) == (asked.start, asked.end):
            asked.registration_id = obsolete.id
            asked.cancel = manages or obsolete.user_id == user.id
            return asked
    raise NotFoundException("No occurrence at this time.")


_PREFERENCE_ORDER: dict[PreferenceValue | None, int] = {
    "preferred": 0,
    "possible": 1,
    None: 2,
    "unavailable": 3,
}


def _note_attribute(note: str) -> Markup:
    """The note, escaped for an attribute, its line breaks as character references, so that
    they survive the response being sent on one line."""
    return escape(note).replace("\r", Markup("&#13;")).replace("\n", Markup("&#10;"))


def _names(
    language: Language, association: AssociationDetail, facts: list[MemberFacts]
) -> list[_Name]:
    """The members' names of the manager's menu, sorted by R27."""
    display_names = {m.user_id: m.display_name for m in association.members}
    names = []
    for fact in facts:
        absence = ""
        if fact.absence is not None:
            first, last = fact.absence.first, fact.absence.last
            absence = (
                translate(language, "schedule.absentOn", date=format_day(language, first))
                if first == last
                else translate(
                    language,
                    "schedule.absentFrom",
                    first=format_day(language, first),
                    last=format_day(language, last),
                )
            )
        names.append(
            _Name(
                user_id=fact.user_id,
                name=display_names.get(fact.user_id, ""),
                count=fact.count,
                preference=fact.preference,
                absence=absence,
                note=_note_attribute(fact.note) if fact.note.strip() else Markup(""),
            )
        )
    return sorted(
        names,
        key=lambda n: (
            bool(n.absence),
            0 if n.absence else _PREFERENCE_ORDER[n.preference],
            n.count or 0,
            name_key(n.name),
        ),
    )


async def _weeks_event(
    request: Request[Any, Any, Any],
    service: PlanningService,
    user: User,
    association: AssociationDetail,
    first: date,
    last: date,
) -> DatastarEvent:
    """The weeks from `first` to `last` as they now are."""
    schedule = await service.schedule(user, association.id, first, last)
    period = await service.get_planning_period(user, association.id)
    shown = fragment(
        request,
        "schedule_weeks.html",
        association=association,
        view=_weeks_view(schedule, period, _today(association)),
    )
    return ServerSentEventGenerator.patch_elements(_one_line(shown))


async def _weeks_patched(
    request: Request[Any, Any, Any],
    service: PlanningService,
    user: User,
    association: AssociationDetail,
    first: date,
    last: date,
    close: str,
) -> DatastarResponse:
    """Closes the menu, or the confirmation, then shows the weeks from `first` to `last` as
    they now are."""
    return DatastarResponse(
        [
            ServerSentEventGenerator.execute_script(close),
            await _weeks_event(request, service, user, association, first, last),
        ]
    )


async def _refused_weeks(
    request: Request[Any, Any, Any],
    service: PlanningService,
    user: User,
    association: AssociationDetail,
    first: date,
    last: date,
    error_id: str,
    key: str,
) -> DatastarResponse:
    """The message of a refused try, whose menu or confirmation stays open, and the weeks as
    they now are."""
    message = translate(interface_language(request), key)
    error = ServerSentEventGenerator.patch_elements(
        fragment(request, "form_error.html", message=message, error_id=error_id)
    )
    return DatastarResponse(
        [error, await _weeks_event(request, service, user, association, first, last)]
    )


def _menu_message(request: Request[Any, Any, Any], asked: _Menu | None, key: str) -> DatastarEvent:
    """The menu with its title and a message only."""
    message = translate(interface_language(request), key)
    body = fragment(request, "schedule_menu.html", menu=None, asked=asked, message=message)
    return ServerSentEventGenerator.patch_elements(_one_line(body))


async def _past_in_menu(
    request: Request[Any, Any, Any],
    service: PlanningService,
    user: User,
    association: AssociationDetail,
    first: date,
    last: date,
    asked: _Menu,
) -> DatastarResponse:
    """The menu shows only its title and "This day is past.", and the weeks as they now are."""
    return DatastarResponse(
        [
            _menu_message(request, asked, "schedule.past"),
            await _weeks_event(request, service, user, association, first, last),
        ]
    )


_CLOSE_MENU = "document.getElementById('occurrence-menu').hidePopover()"
_CLOSE_CANCEL = "document.getElementById('cancel-registration').close()"


@post("/association/{slug:str}/menu", status_code=200)
async def occurrence_menu(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    asked: _Menu | None = None
    try:
        signals = await read_signals_dict(request)
        day, start, end = _asked_occurrence(signals)
        asked = _Menu(date=day, start=start, end=end)
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        service = PlanningService(db_session)
        if "from" in signals or "to" in signals:
            first, last = _shown_range(signals)
        else:
            opened = await service.schedule(user, association.id, None, None)
            first, last = opened.from_, opened.to
        if day < _today(association):
            return await _past_in_menu(request, service, user, association, first, last, asked)
        schedule = await service.schedule(user, association.id, day, day)
        manages = association.role == "manager"
        menu = _menu_of(schedule, user, manages, asked)
        if manages and (menu.sign_up or menu.taken_by is not None):
            facts = await service.member_facts(user, association.id, day, start, end)
            facts = [f for f in facts if f.user_id != menu.taken_by]
            menu.names = _names(interface_language(request), association, facts)
        if menu.taken_by is not None:
            menu.taken_by_name = next(
                (m.display_name for m in association.members if m.user_id == menu.taken_by), ""
            )
    except _REFUSALS:
        return DatastarResponse(_menu_message(request, asked, "error"))
    weeks = {"from": first.isoformat(), "to": last.isoformat()}
    context = {
        "association": association,
        "menu": menu,
        "weeks": weeks,
        "message": "",
        "user_id": user.id,
    }
    events = [
        ServerSentEventGenerator.patch_elements(
            _one_line(fragment(request, "schedule_menu.html", **context))
        )
    ]
    if menu.cancel:
        events.append(
            ServerSentEventGenerator.patch_elements(
                _one_line(fragment(request, "schedule_cancel.html", **context))
            )
        )
    return DatastarResponse(events)


@post("/association/{slug:str}/sign-up", status_code=200)
async def schedule_sign_up(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        signals = await read_signals_dict(request)
        day, start, end = _asked_occurrence(signals)
        first, last = _shown_range(signals)
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        service = PlanningService(db_session)
        await service.register(user, association.id, user.id, day, start, end)
    except TakenException:
        return await _refused_weeks(
            request, service, user, association, first, last, "menu-error", "schedule.taken"
        )
    except PastException:
        asked = _Menu(date=day, start=start, end=end)
        return await _past_in_menu(request, service, user, association, first, last, asked)
    except _REFUSALS:
        return _error(request, "menu-error", "error")
    return await _weeks_patched(request, service, user, association, first, last, _CLOSE_MENU)


@post("/association/{slug:str}/propose", status_code=200)
async def schedule_propose(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: FromPath[str]
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id, close = "menu-error", _CLOSE_MENU
    try:
        signals = await read_signals_dict(request)
        day, start, end = _asked_occurrence(signals)
        first, last = _shown_range(signals)
        if "replacing" in signals:
            error_id = f"move-error-{signals.get('user_id')}"
        try:
            user_id = UUID(signals.get("user_id"))
            replacing = signals.get("replacing")
            replaced = None if replacing is None else UUID(replacing)
        except (TypeError, ValueError) as error:
            raise ClientException("Give the member's user_id.") from error
        take_over_close = f"document.getElementById('take-over').close(); {_CLOSE_MENU}"
        if replaced is not None and signals.get("take_over") is True:
            error_id, close = "take-over-error", take_over_close
        elif replaced is not None:
            error_id = f"move-error-{user_id}"
            close = f"document.getElementById('move-{user_id}').close(); {_CLOSE_MENU}"
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        # Without the flag, a volunteer replacing for themself can only be taking over.
        if replaced is not None and user_id == user.id and association.role != "manager":
            error_id, close = "take-over-error", take_over_close
        service = PlanningService(db_session)
        await service.register(user, association.id, user_id, day, start, end, replaced)
    except TakenException:
        return await _refused_weeks(
            request, service, user, association, first, last, error_id, "schedule.taken"
        )
    except PastException:
        if error_id == "menu-error":
            asked = _Menu(date=day, start=start, end=end)
            return await _past_in_menu(request, service, user, association, first, last, asked)
        return await _refused_weeks(
            request, service, user, association, first, last, error_id, "schedule.past"
        )
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _weeks_patched(request, service, user, association, first, last, close)


async def _status_changed(
    request: Request[Any, Any, Any],
    db_session: AsyncSession,
    slug: str,
    registration_id: str,
    status: Status,
) -> DatastarResponse:
    """Confirms or cancels a registration (R7), then shows the weeks shown as they now are."""
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "menu-error" if status == "confirmed" else "cancel-registration-error"
    try:
        first, last = _shown_range(await read_signals_dict(request))
        try:
            registration = UUID(registration_id)
        except ValueError as error:
            raise NotFoundException("Registration not found.") from error
        association = await AssociationService(db_session).detail_by_ref(
            user, association_ref(request, slug)
        )
        service = PlanningService(db_session)
        await service.change_status(user, association.id, registration, status)
    except PastException:
        return await _refused_weeks(
            request, service, user, association, first, last, error_id, "schedule.past"
        )
    except _REFUSALS:
        return _error(request, error_id, "error")
    close = _CLOSE_MENU if status == "confirmed" else _CLOSE_CANCEL
    return await _weeks_patched(request, service, user, association, first, last, close)


@post("/association/{slug:str}/registrations/{registration_id:str}/confirm", status_code=200)
async def confirm_registration(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: FromPath[str],
    registration_id: FromPath[str],
) -> DatastarResponse:
    return await _status_changed(request, db_session, slug, registration_id, "confirmed")


@post("/association/{slug:str}/registrations/{registration_id:str}/cancel", status_code=200)
async def cancel_registration(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: FromPath[str],
    registration_id: FromPath[str],
) -> DatastarResponse:
    return await _status_changed(request, db_session, slug, registration_id, "cancelled")
