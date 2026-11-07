import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo

import msgspec
from datastar_py.litestar import DatastarResponse, ServerSentEventGenerator
from litestar import Request, get, post
from litestar.di import NamedDependency
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from litestar.response import Template
from markupsafe import Markup, escape
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.controllers import find_current_user
from gilda.core.models import User
from gilda.core.pages import members_in_order
from gilda.core.schemas import AssociationDetail
from gilda.core.services import AssociationService, ConflictException
from gilda.mailer import Language
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
from gilda.planning.services import PlanningService, TakenException
from gilda.web.rendering import (
    format_day,
    fragment,
    interface_language,
    page,
    read_signals_dict,
    translate,
)

# An action that fails on these shows the generic error.
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


# Members' preferences


@post("/association/{slug:str}/settings/preferences/{slot_id:str}/{user_id:str}", status_code=200)
async def choose_member_preference(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    slot_id: str,
    user_id: str,
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "members-preferences-error"
    value = (await read_signals_dict(request)).get("value")
    if value not in ("", "preferred", "possible", "unavailable"):
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
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
    shown = fragment(
        request,
        "member_preference_select.html",
        association=association,
        slot=slot,
        member=member,
        values=await _all_preferences(service, user, association),
    )
    return DatastarResponse(
        [
            ServerSentEventGenerator.patch_elements(_one_line(shown)),
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
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
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
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).set_planning_period(
            user, association.id, asked.first, asked.last
        )
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _period_patched(request, db_session, user, association, "edit-period")


@post("/association/{slug:str}/settings/period/clear", status_code=200)
async def clear_period(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
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
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
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
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).add_closure(
            user, association.id, asked.first, asked.last, asked.label
        )
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _closures_patched(request, db_session, user, association, "add-closure")


@post("/association/{slug:str}/settings/closures/{closure_id:str}/edit", status_code=200)
async def edit_closure(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    closure_id: str,
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
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).edit_closure(
            user, association.id, _closure_id(closure_id), asked.first, asked.last, asked.label
        )
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _closures_patched(request, db_session, user, association, "edit-closure")


@post("/association/{slug:str}/settings/closures/{closure_id:str}/delete", status_code=200)
async def delete_closure(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    closure_id: str,
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).delete_closure(
            user, association.id, _closure_id(closure_id)
        )
    except _REFUSALS:
        return _error(request, "delete-closure-error", "error")
    return await _closures_patched(request, db_session, user, association, "delete-closure")


# My availability


async def _own_preferences(
    service: PlanningService, user: User, association_id: UUID
) -> dict[UUID, str]:
    """The user's own preference on each slot that has one."""
    preferences = await service.list_preferences(user, association_id)
    return {p.slot_id: p.value for p in preferences if p.user_id == user.id}


@get("/association/{slug:str}/availability")
async def availability_page(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
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
    slug: str,
    slot_id: str,
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "preferences-error"
    value = (await read_signals_dict(request)).get("value")
    if value not in ("", "preferred", "possible", "unavailable"):
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
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
    shown = fragment(
        request,
        "preference_select.html",
        association=association,
        slot=slot,
        values=await _own_preferences(service, user, association.id),
    )
    return DatastarResponse(
        [
            ServerSentEventGenerator.patch_elements(_one_line(shown)),
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
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
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
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).add_absence(user, association.id, asked.first, asked.last)
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _absences_patched(request, db_session, user, association, "add-absence")


@post("/association/{slug:str}/availability/absences/{absence_id:str}/edit", status_code=200)
async def edit_absence(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    absence_id: str,
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
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).edit_absence(
            user, association.id, _absence_id(absence_id), asked.first, asked.last
        )
    except _REFUSALS:
        return _error(request, error_id, "error")
    return await _absences_patched(request, db_session, user, association, "edit-absence")


@post("/association/{slug:str}/availability/absences/{absence_id:str}/delete", status_code=200)
async def delete_absence(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    absence_id: str,
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).delete_absence(
            user, association.id, _absence_id(absence_id)
        )
    except _REFUSALS:
        return _error(request, "delete-absence-error", "error")
    return await _absences_patched(request, db_session, user, association, "delete-absence")


# My availability: Note for the managers


@post("/association/{slug:str}/availability/note", status_code=200)
async def save_note(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "edit-note-error"
    text = (await read_signals_dict(request)).get("text")
    if not isinstance(text, str):
        return _error(request, error_id, "error")
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        await PlanningService(db_session).set_note(user, association.id, text)
    except _REFUSALS:
        return _error(request, error_id, "error")
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
    closure: ClosureRead | None
    past: bool
    within: bool
    after: bool

    @property
    def lanes(self) -> int:
        return max([1, *(item.lanes for item in self.items)])


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
    columns = sorted({item.date.weekday() for item in items})
    view.columns = len(columns)
    monday = first
    while monday <= last:
        days = []
        for column in columns:
            day = monday + timedelta(days=column)
            days.append(
                _Day(
                    date=day,
                    items=by_date.get(day, []),
                    closure=next((c for c in schedule.closures if c.first <= day <= c.last), None),
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


def _today(association: AssociationDetail) -> date:
    return datetime.now(ZoneInfo(association.timezone)).date()


@get("/association/{slug:str}")
async def schedule_page(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> Template:
    user = await find_current_user(request, db_session)
    if user is None:
        return page(request, "sign_in.html", message="")
    try:
        association = await AssociationService(db_session).detail_by_slug(user, slug)
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
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    error_id = "weeks-error"
    try:
        first, last = _shown_range(await read_signals_dict(request))
        association = await AssociationService(db_session).detail_by_slug(user, slug)
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
        asked.registration_id = registration.id
        asked.confirm = allowed and registration.status == "proposed"
        asked.cancel = allowed
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
            n.name.casefold(),
        ),
    )


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
    schedule = await service.schedule(user, association.id, first, last)
    period = await service.get_planning_period(user, association.id)
    shown = fragment(
        request,
        "schedule_weeks.html",
        association=association,
        view=_weeks_view(schedule, period, _today(association)),
    )
    return DatastarResponse(
        [
            ServerSentEventGenerator.execute_script(close),
            ServerSentEventGenerator.patch_elements(_one_line(shown)),
        ]
    )


_CLOSE_MENU = "document.getElementById('occurrence-menu').hidePopover()"
_CLOSE_CANCEL = "document.getElementById('cancel-registration').close()"


@post("/association/{slug:str}/menu", status_code=200)
async def occurrence_menu(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    show = ServerSentEventGenerator.execute_script(
        "document.getElementById('occurrence-menu').showPopover()"
    )
    try:
        signals = await read_signals_dict(request)
        day, start, end = _asked_occurrence(signals)
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        service = PlanningService(db_session)
        if "from" in signals or "to" in signals:
            first, last = _shown_range(signals)
        else:
            opened = await service.schedule(user, association.id, None, None)
            first, last = opened.from_, opened.to
        schedule = await service.schedule(user, association.id, day, day)
        manages = association.role == "manager"
        menu = _menu_of(schedule, user, manages, _Menu(date=day, start=start, end=end))
        if manages and menu.sign_up:
            facts = await service.member_facts(user, association.id, day, start, end)
            menu.names = _names(interface_language(request), association, facts)
    except _REFUSALS:
        message = translate(interface_language(request), "error")
        body = fragment(request, "schedule_menu.html", menu=None, message=message)
        return DatastarResponse([ServerSentEventGenerator.patch_elements(_one_line(body)), show])
    weeks = {"from": first.isoformat(), "to": last.isoformat()}
    context = {"association": association, "menu": menu, "weeks": weeks, "message": ""}
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
    return DatastarResponse([*events, show])


@post("/association/{slug:str}/sign-up", status_code=200)
async def schedule_sign_up(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        signals = await read_signals_dict(request)
        day, start, end = _asked_occurrence(signals)
        first, last = _shown_range(signals)
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        service = PlanningService(db_session)
        await service.register(user, association.id, user.id, day, start, end)
    except TakenException:
        return _error(request, "menu-error", "schedule.taken")
    except _REFUSALS:
        return _error(request, "menu-error", "error")
    return await _weeks_patched(request, service, user, association, first, last, _CLOSE_MENU)


@post("/association/{slug:str}/propose", status_code=200)
async def schedule_propose(
    request: Request[Any, Any, Any], db_session: NamedDependency[AsyncSession], slug: str
) -> DatastarResponse:
    user = await find_current_user(request, db_session)
    if user is None:
        return DatastarResponse(ServerSentEventGenerator.redirect("/"))
    try:
        signals = await read_signals_dict(request)
        day, start, end = _asked_occurrence(signals)
        first, last = _shown_range(signals)
        try:
            user_id = UUID(signals.get("user_id"))
        except (TypeError, ValueError) as error:
            raise ClientException("Give the member's user_id.") from error
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        service = PlanningService(db_session)
        await service.register(user, association.id, user_id, day, start, end)
    except TakenException:
        return _error(request, "menu-error", "schedule.taken")
    except _REFUSALS:
        return _error(request, "menu-error", "error")
    return await _weeks_patched(request, service, user, association, first, last, _CLOSE_MENU)


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
        association = await AssociationService(db_session).detail_by_slug(user, slug)
        service = PlanningService(db_session)
        await service.change_status(user, association.id, registration, status)
    except _REFUSALS:
        return _error(request, error_id, "error")
    close = _CLOSE_MENU if status == "confirmed" else _CLOSE_CANCEL
    return await _weeks_patched(request, service, user, association, first, last, close)


@post("/association/{slug:str}/registrations/{registration_id:str}/confirm", status_code=200)
async def confirm_registration(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    registration_id: str,
) -> DatastarResponse:
    return await _status_changed(request, db_session, slug, registration_id, "confirmed")


@post("/association/{slug:str}/registrations/{registration_id:str}/cancel", status_code=200)
async def cancel_registration(
    request: Request[Any, Any, Any],
    db_session: NamedDependency[AsyncSession],
    slug: str,
    registration_id: str,
) -> DatastarResponse:
    return await _status_changed(request, db_session, slug, registration_id, "cancelled")
