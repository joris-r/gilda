from datetime import date, datetime, time, timedelta
from typing import cast, get_args
from uuid import UUID
from zoneinfo import ZoneInfo

from advanced_alchemy.exceptions import IntegrityError
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import Association, Membership, User
from gilda.core.repositories import MembershipRepository
from gilda.core.services import ConflictException
from gilda.planning.models import (
    Absence,
    Closure,
    PlanningPeriod,
    Preference,
    Registration,
    Slot,
)
from gilda.planning.repositories import (
    AbsenceRepository,
    ClosureRepository,
    NoteRepository,
    PlanningPeriodRepository,
    PreferenceRepository,
    RegistrationRepository,
    SlotRepository,
)
from gilda.planning.schemas import (
    AbsenceRead,
    ClosureRead,
    MemberAbsenceRead,
    MemberNote,
    NoteData,
    OccurrenceRead,
    OccurrenceRegistration,
    PlanningPeriodData,
    PlanningPeriodSummary,
    PlanningSummary,
    PreferenceRead,
    PreferenceValue,
    RegistrationCount,
    RegistrationRead,
    ScheduleRead,
    SlotRead,
    Status,
    Weekday,
)

WEEKDAYS: tuple[Weekday, ...] = get_args(Weekday)
# Confirmed registrations show at least this many days ahead, further to the planning period's end.
UPCOMING_DAYS = 27


def clock(value: time) -> str:
    return value.strftime("%H:%M")


def parse_clock(value: str) -> time:
    return time.fromisoformat(value)


def slot_read(slot: Slot) -> SlotRead:
    return SlotRead(
        id=slot.id, weekday=WEEKDAYS[slot.weekday], start=clock(slot.start), end=clock(slot.end)
    )


def set_closure(closure: Closure, first: date, last: date, label: str | None) -> None:
    if last < first:
        raise ClientException("The last date must not be before the first.")
    closure.first, closure.last, closure.label = first, last, label


def closure_read(closure: Closure) -> ClosureRead:
    return ClosureRead(id=closure.id, first=closure.first, last=closure.last, label=closure.label)


def set_absence(absence: Absence, first: date, last: date) -> None:
    if last < first:
        raise ClientException("The last date must not be before the first.")
    absence.first, absence.last = first, last


def absence_read(absence: Absence) -> AbsenceRead:
    return AbsenceRead(id=absence.id, first=absence.first, last=absence.last)


def preference_read(preference: Preference) -> PreferenceRead:
    return PreferenceRead(
        user_id=preference.user_id,
        slot_id=preference.slot_id,
        value=cast(PreferenceValue, preference.value),
    )


def registration_read(registration: Registration) -> RegistrationRead:
    return RegistrationRead(
        id=registration.id,
        user_id=registration.user_id,
        display_name=registration.user.display_name,
        status=cast(Status, registration.status),
        date=registration.date,
        start=clock(registration.start),
        end=clock(registration.end),
    )


def occurrence_registration(registration: Registration) -> OccurrenceRegistration:
    return OccurrenceRegistration(
        id=registration.id,
        user_id=registration.user_id,
        display_name=registration.user.display_name,
        status=cast(Status, registration.status),
    )


class PlanningService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.memberships = MembershipRepository(session=db_session)
        self.slots = SlotRepository(session=db_session)
        self.closures = ClosureRepository(session=db_session)
        self.registrations = RegistrationRepository(session=db_session)
        self.planning_periods = PlanningPeriodRepository(session=db_session)
        self.preferences = PreferenceRepository(session=db_session)
        self.absences = AbsenceRepository(session=db_session)
        self.notes = NoteRepository(session=db_session)

    # Slots

    async def list_slots(self, user: User, association_id: UUID) -> list[SlotRead]:
        await self._membership_of(user, association_id)
        return [slot_read(s) for s in await self._slots(association_id)]

    async def add_slot(
        self, user: User, association_id: UUID, weekday: Weekday, start: str, end: str
    ) -> SlotRead:
        await self._manager_of(user, association_id)
        slot = Slot(association_id=association_id)
        await self._set_slot(slot, weekday, start, end)
        return slot_read(await self.slots.add(slot))

    async def edit_slot(
        self,
        user: User,
        association_id: UUID,
        slot_id: UUID,
        weekday: Weekday,
        start: str,
        end: str,
    ) -> SlotRead:
        await self._manager_of(user, association_id)
        slot = await self._slot(association_id, slot_id)
        await self._set_slot(slot, weekday, start, end)
        return slot_read(await self.slots.update(slot))

    async def delete_slot(self, user: User, association_id: UUID, slot_id: UUID) -> None:
        await self._manager_of(user, association_id)
        slot = await self._slot(association_id, slot_id)
        await self.slots.delete(slot.id)

    async def _slot(self, association_id: UUID, slot_id: UUID) -> Slot:
        slot = await self.slots.get_one_or_none(id=slot_id, association_id=association_id)
        if slot is None:
            raise NotFoundException("Slot not found.")
        return slot

    async def _set_slot(self, slot: Slot, weekday: Weekday, start: str, end: str) -> None:
        """Gives `slot` these values, unless they are invalid or another slot has them."""
        start_time, end_time = parse_clock(start), parse_clock(end)
        if start_time >= end_time:
            raise ClientException("The start must be before the end.")
        weekday_index = WEEKDAYS.index(weekday)
        same = await self.slots.get_one_or_none(
            association_id=slot.association_id,
            weekday=weekday_index,
            start=start_time,
            end=end_time,
        )
        if same is not None and same.id != slot.id:
            raise ConflictException("This slot already exists.")
        slot.weekday, slot.start, slot.end = weekday_index, start_time, end_time

    # Preferences

    async def list_preferences(self, user: User, association_id: UUID) -> list[PreferenceRead]:
        own = await self._membership_of(user, association_id)
        conditions: list[ColumnElement[bool]] = [
            Preference.slot_id.in_([s.id for s in await self._slots(association_id)])
        ]
        if own.role != "manager":
            conditions.append(Preference.user_id == user.id)
        return [preference_read(p) for p in await self.preferences.list(*conditions)]

    async def set_preference(
        self,
        user: User,
        association_id: UUID,
        slot_id: UUID,
        user_id: UUID,
        value: PreferenceValue,
    ) -> PreferenceRead:
        await self._preference_target(user, association_id, slot_id, user_id)
        await self.preferences.set_value(slot_id, user_id, value)
        return PreferenceRead(user_id=user_id, slot_id=slot_id, value=value)

    async def delete_preference(
        self, user: User, association_id: UUID, slot_id: UUID, user_id: UUID
    ) -> None:
        await self._preference_target(user, association_id, slot_id, user_id)
        await self.preferences.delete_where(slot_id=slot_id, user_id=user_id)

    async def _preference_target(
        self, user: User, association_id: UUID, slot_id: UUID, user_id: UUID
    ) -> None:
        own = await self._membership_of(user, association_id)
        if not await self.slots.exists(id=slot_id, association_id=association_id):
            raise NotFoundException("Slot not found.")
        if not await self.memberships.exists(user_id=user_id, association_id=association_id):
            raise NotFoundException("Member not found.")
        if user_id != user.id and own.role != "manager":
            raise PermissionDeniedException("Only managers can change another member's preference.")

    # Registration counts

    async def registration_counts(
        self, user: User, association_id: UUID
    ) -> list[RegistrationCount] | None:
        await self._manager_of(user, association_id)
        period = await self.planning_periods.get_one_or_none(association_id=association_id)
        if period is None:
            return None
        registrations = await self._live(
            association_id,
            await self.registrations.list(
                Registration.association_id == association_id,
                Registration.status != "cancelled",
                Registration.date >= period.first,
                Registration.date <= period.last,
            ),
        )
        memberships = await self.memberships.list(association_id=association_id)
        return [
            RegistrationCount(
                user_id=m.user_id, count=sum(r.user_id == m.user_id for r in registrations)
            )
            for m in memberships
        ]

    # Closures

    async def list_closures(self, user: User, association_id: UUID) -> list[ClosureRead]:
        await self._membership_of(user, association_id)
        closures = await self.closures.list(association_id=association_id)
        return [closure_read(c) for c in sorted(closures, key=lambda c: (c.first, c.last))]

    async def add_closure(
        self, user: User, association_id: UUID, first: date, last: date, label: str | None
    ) -> ClosureRead:
        await self._manager_of(user, association_id)
        closure = Closure(association_id=association_id)
        set_closure(closure, first, last, label)
        return closure_read(await self.closures.add(closure))

    async def edit_closure(
        self,
        user: User,
        association_id: UUID,
        closure_id: UUID,
        first: date,
        last: date,
        label: str | None,
    ) -> ClosureRead:
        await self._manager_of(user, association_id)
        closure = await self._closure(association_id, closure_id)
        set_closure(closure, first, last, label)
        return closure_read(await self.closures.update(closure))

    async def delete_closure(self, user: User, association_id: UUID, closure_id: UUID) -> None:
        await self._manager_of(user, association_id)
        closure = await self._closure(association_id, closure_id)
        await self.closures.delete(closure.id)

    async def _closure(self, association_id: UUID, closure_id: UUID) -> Closure:
        closure = await self.closures.get_one_or_none(id=closure_id, association_id=association_id)
        if closure is None:
            raise NotFoundException("Closure not found.")
        return closure

    # Absences, each the user's own

    async def list_absences(self, user: User, association_id: UUID) -> list[AbsenceRead]:
        await self._membership_of(user, association_id)
        absences = await self.absences.list(association_id=association_id, user_id=user.id)
        return [absence_read(a) for a in sorted(absences, key=lambda a: (a.first, a.last))]

    async def list_member_absences(
        self, user: User, association_id: UUID
    ) -> list[MemberAbsenceRead]:
        await self._manager_of(user, association_id)
        absences = await self.absences.list(association_id=association_id)
        return [
            MemberAbsenceRead(id=a.id, user_id=a.user_id, first=a.first, last=a.last)
            for a in sorted(absences, key=lambda a: (a.first, a.last))
        ]

    async def add_absence(
        self, user: User, association_id: UUID, first: date, last: date
    ) -> AbsenceRead:
        await self._membership_of(user, association_id)
        absence = Absence(association_id=association_id, user_id=user.id)
        set_absence(absence, first, last)
        return absence_read(await self.absences.add(absence))

    async def edit_absence(
        self, user: User, association_id: UUID, absence_id: UUID, first: date, last: date
    ) -> AbsenceRead:
        absence = await self._absence(user, association_id, absence_id)
        set_absence(absence, first, last)
        return absence_read(await self.absences.update(absence))

    async def delete_absence(self, user: User, association_id: UUID, absence_id: UUID) -> None:
        absence = await self._absence(user, association_id, absence_id)
        await self.absences.delete(absence.id)

    async def _absence(self, user: User, association_id: UUID, absence_id: UUID) -> Absence:
        await self._membership_of(user, association_id)
        absence = await self.absences.get_one_or_none(
            id=absence_id, association_id=association_id, user_id=user.id
        )
        if absence is None:
            raise NotFoundException("Absence not found.")
        return absence

    # Note, the user's own

    async def get_note(self, user: User, association_id: UUID) -> NoteData:
        await self._membership_of(user, association_id)
        note = await self.notes.get_one_or_none(association_id=association_id, user_id=user.id)
        return NoteData(text=note.text if note else "")

    async def list_notes(self, user: User, association_id: UUID) -> list[MemberNote]:
        await self._manager_of(user, association_id)
        notes = {n.user_id: n.text for n in await self.notes.list(association_id=association_id)}
        memberships = await self.memberships.list(association_id=association_id)
        return [MemberNote(user_id=m.user_id, text=notes.get(m.user_id, "")) for m in memberships]

    async def set_note(self, user: User, association_id: UUID, text: str) -> NoteData:
        await self._membership_of(user, association_id)
        await self.notes.set_text(association_id, user.id, text)
        return NoteData(text=text)

    # Planning period

    async def get_planning_period(
        self, user: User, association_id: UUID
    ) -> PlanningPeriodData | None:
        await self._membership_of(user, association_id)
        period = await self.planning_periods.get_one_or_none(association_id=association_id)
        return None if period is None else PlanningPeriodData(first=period.first, last=period.last)

    async def set_planning_period(
        self, user: User, association_id: UUID, first: date, last: date
    ) -> PlanningPeriodData:
        await self._manager_of(user, association_id)
        if last < first:
            raise ClientException("The last date must not be before the first.")
        period = await self.planning_periods.get_one_or_none(association_id=association_id)
        if period is None:
            await self.planning_periods.add(
                PlanningPeriod(association_id=association_id, first=first, last=last)
            )
        else:
            period.first, period.last = first, last
            await self.planning_periods.update(period)
        return PlanningPeriodData(first=first, last=last)

    async def clear_planning_period(self, user: User, association_id: UUID) -> None:
        await self._manager_of(user, association_id)
        await self.planning_periods.delete_where(association_id=association_id)

    # Schedule

    async def schedule(
        self, user: User, association_id: UUID, first: date, last: date
    ) -> ScheduleRead:
        await self._membership_of(user, association_id)
        slots = await self._slots(association_id)
        closures = await self._closures_between(association_id, first, last)
        registrations = await self.registrations.list(
            Registration.association_id == association_id,
            Registration.date >= first,
            Registration.date <= last,
        )
        # UUIDv7 ids grow with time, so the last of a list is the latest.
        registrations.sort(key=lambda r: r.id)

        occurrences: list[OccurrenceRead] = []
        for day in _dates(first, last):
            if any(c.first <= day <= c.last for c in closures):
                continue
            for slot in slots:
                if slot.weekday != day.weekday():
                    continue
                same = [
                    r
                    for r in registrations
                    if (r.date, r.start, r.end) == (day, slot.start, slot.end)
                ]
                live = [r for r in same if r.status != "cancelled"]
                shown = live[0] if live else (same[-1] if same else None)
                occurrences.append(
                    OccurrenceRead(
                        date=day,
                        start=clock(slot.start),
                        end=clock(slot.end),
                        registration=occurrence_registration(shown) if shown else None,
                    )
                )

        matched = {(o.date, o.start, o.end) for o in occurrences}
        obsolete = sorted(
            (
                r
                for r in registrations
                if r.status != "cancelled" and (r.date, clock(r.start), clock(r.end)) not in matched
            ),
            key=lambda r: (r.date, r.start),
        )
        return ScheduleRead(
            occurrences=occurrences,
            obsolete=[registration_read(r) for r in obsolete],
            closures=[closure_read(c) for c in closures],
        )

    # Summary

    async def summary(self, user: User, association: Association) -> PlanningSummary:
        """What concerns `user` in `association`, for My associations."""
        today = datetime.now(ZoneInfo(association.timezone)).date()
        period = await self.planning_periods.get_one_or_none(association_id=association.id)
        since = today if period is None else min(today, period.first)
        registrations = await self.registrations.list(
            Registration.association_id == association.id,
            Registration.user_id == user.id,
            Registration.status != "cancelled",
            Registration.date >= since,
        )
        live = await self._live(association.id, registrations)

        until = today + timedelta(days=UPCOMING_DAYS)
        if period is not None:
            until = max(until, period.last)
        upcoming = sorted(
            (r for r in live if r.date >= today and (r.status == "proposed" or r.date <= until)),
            key=lambda r: (r.date, r.start),
        )
        return PlanningSummary(
            upcoming=[registration_read(r) for r in upcoming],
            planning_period=None
            if period is None
            else PlanningPeriodSummary(
                first=period.first,
                last=period.last,
                registrations=sum(period.first <= r.date <= period.last for r in live),
            ),
        )

    # Registrations

    async def register(
        self, user: User, association_id: UUID, user_id: UUID, day: date, start: str, end: str
    ) -> RegistrationRead:
        own = await self._membership_of(user, association_id)
        myself = user_id == user.id
        if not myself and own.role != "manager":
            raise PermissionDeniedException("Only managers can register another member.")
        if not await self.memberships.exists(user_id=user_id, association_id=association_id):
            raise ClientException("This user is not a member of the association.")
        if day < datetime.now(ZoneInfo(own.association.timezone)).date():
            raise ConflictException("This date is past.")
        start_time, end_time = parse_clock(start), parse_clock(end)
        if not await self._is_occurrence(association_id, day, start_time, end_time):
            raise ConflictException("There is no opening at this time.")
        try:
            registration = await self.registrations.add(
                Registration(
                    association_id=association_id,
                    user_id=user_id,
                    date=day,
                    start=start_time,
                    end=end_time,
                    status="confirmed" if myself else "proposed",
                ),
                auto_refresh=True,
            )
        except IntegrityError as error:
            raise ConflictException("Someone is already registered at this time.") from error
        return registration_read(registration)

    async def change_status(
        self, user: User, association_id: UUID, registration_id: UUID, status: Status
    ) -> RegistrationRead:
        own = await self._membership_of(user, association_id)
        registration = await self.registrations.get_one_or_none(
            id=registration_id, association_id=association_id
        )
        if registration is None:
            raise NotFoundException("Registration not found.")
        mine = registration.user_id == user.id
        if status == "confirmed":
            if not mine and own.role != "manager":
                raise PermissionDeniedException(
                    "Only the registered member or a manager can confirm."
                )
            if registration.status != "proposed" or not await self._is_occurrence(
                association_id, registration.date, registration.start, registration.end
            ):
                raise ConflictException("Only a proposed registration can be confirmed.")
        elif status == "cancelled":
            if not mine and own.role != "manager":
                raise PermissionDeniedException(
                    "Only the registered member or a manager can cancel."
                )
            if registration.status == "cancelled":
                raise ConflictException("This registration is already cancelled.")
        else:
            raise ConflictException("A registration cannot go back to proposed.")
        registration.status = status
        return registration_read(await self.registrations.update(registration))

    # Helpers

    async def _slots(self, association_id: UUID) -> list[Slot]:
        slots = await self.slots.list(association_id=association_id)
        return sorted(slots, key=lambda s: (s.weekday, s.start, s.end))

    async def _closures_between(
        self, association_id: UUID, first: date, last: date
    ) -> list[Closure]:
        closures = await self.closures.list(
            Closure.association_id == association_id, Closure.first <= last, Closure.last >= first
        )
        return sorted(closures, key=lambda c: (c.first, c.last))

    async def _live(
        self, association_id: UUID, registrations: list[Registration]
    ) -> list[Registration]:
        """The registrations that are not obsolete: on a slot, outside every closure."""
        if not registrations:
            return []
        slots = {(s.weekday, s.start, s.end) for s in await self._slots(association_id)}
        closures = await self._closures_between(
            association_id,
            min(r.date for r in registrations),
            max(r.date for r in registrations),
        )
        return [
            r
            for r in registrations
            if (r.date.weekday(), r.start, r.end) in slots
            and not any(c.first <= r.date <= c.last for c in closures)
        ]

    async def _is_occurrence(self, association_id: UUID, day: date, start: time, end: time) -> bool:
        if await self._closures_between(association_id, day, day):
            return False
        return await self.slots.exists(
            association_id=association_id, weekday=day.weekday(), start=start, end=end
        )

    async def _membership_of(self, user: User, association_id: UUID) -> Membership:
        membership = await self.memberships.get_one_or_none(
            user_id=user.id, association_id=association_id
        )
        if membership is None:
            raise NotFoundException("Association not found.")
        return membership

    async def _manager_of(self, user: User, association_id: UUID) -> Membership:
        membership = await self._membership_of(user, association_id)
        if membership.role != "manager":
            raise PermissionDeniedException("Only managers can do this.")
        return membership


def _dates(first: date, last: date) -> list[date]:
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]


async def end_membership(db_session: AsyncSession, association: Association, user_id: UUID) -> None:
    """R28: the user leaves the association's planning."""
    today = datetime.now(ZoneInfo(association.timezone)).date()
    registrations = RegistrationRepository(session=db_session)
    upcoming = await registrations.list(
        Registration.date >= today,
        Registration.status != "cancelled",
        association_id=association.id,
        user_id=user_id,
    )
    for registration in upcoming:
        registration.status = "cancelled"
        await registrations.update(registration)
    slots = await SlotRepository(session=db_session).list(association_id=association.id)
    await PreferenceRepository(session=db_session).delete_where(
        Preference.slot_id.in_([s.id for s in slots]), user_id=user_id
    )
    await AbsenceRepository(session=db_session).delete_where(
        association_id=association.id, user_id=user_id
    )
    await NoteRepository(session=db_session).delete_where(
        association_id=association.id, user_id=user_id
    )
