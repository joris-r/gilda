from datetime import date, time, timedelta
from typing import cast, get_args
from uuid import UUID

from advanced_alchemy.exceptions import IntegrityError
from litestar.exceptions import ClientException, NotFoundException, PermissionDeniedException
from sqlalchemy.ext.asyncio import AsyncSession

from gilda.core.models import Membership, User
from gilda.core.repositories import MembershipRepository
from gilda.core.services import ConflictException
from gilda.planning.models import Closure, Registration, Slot
from gilda.planning.repositories import ClosureRepository, RegistrationRepository, SlotRepository
from gilda.planning.schemas import (
    ClosureRead,
    OccurrenceRead,
    OccurrenceRegistration,
    RegistrationRead,
    ScheduleRead,
    SlotRead,
    Status,
    Weekday,
)

WEEKDAYS: tuple[Weekday, ...] = get_args(Weekday)


def clock(value: time) -> str:
    return value.strftime("%H:%M")


def parse_clock(value: str) -> time:
    return time.fromisoformat(value)


def slot_read(slot: Slot) -> SlotRead:
    return SlotRead(
        id=slot.id, weekday=WEEKDAYS[slot.weekday], start=clock(slot.start), end=clock(slot.end)
    )


def closure_read(closure: Closure) -> ClosureRead:
    return ClosureRead(id=closure.id, first=closure.first, last=closure.last, label=closure.label)


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

    # Slots

    async def list_slots(self, user: User, association_id: UUID) -> list[SlotRead]:
        await self._membership_of(user, association_id)
        return [slot_read(s) for s in await self._slots(association_id)]

    async def add_slot(
        self, user: User, association_id: UUID, weekday: Weekday, start: str, end: str
    ) -> SlotRead:
        await self._manager_of(user, association_id)
        start_time, end_time = parse_clock(start), parse_clock(end)
        if start_time >= end_time:
            raise ClientException("The start must be before the end.")
        weekday_index = WEEKDAYS.index(weekday)
        if await self.slots.exists(
            association_id=association_id, weekday=weekday_index, start=start_time, end=end_time
        ):
            raise ConflictException("This slot already exists.")
        slot = await self.slots.add(
            Slot(
                association_id=association_id, weekday=weekday_index, start=start_time, end=end_time
            )
        )
        return slot_read(slot)

    async def delete_slot(self, user: User, association_id: UUID, slot_id: UUID) -> None:
        await self._manager_of(user, association_id)
        slot = await self.slots.get_one_or_none(id=slot_id, association_id=association_id)
        if slot is None:
            raise NotFoundException("Slot not found.")
        await self.slots.delete(slot.id)

    # Closures

    async def list_closures(self, user: User, association_id: UUID) -> list[ClosureRead]:
        await self._membership_of(user, association_id)
        closures = await self.closures.list(association_id=association_id)
        return [closure_read(c) for c in sorted(closures, key=lambda c: (c.first, c.last))]

    async def add_closure(
        self, user: User, association_id: UUID, first: date, last: date, label: str | None
    ) -> ClosureRead:
        await self._manager_of(user, association_id)
        if last < first:
            raise ClientException("The last date must not be before the first.")
        closure = await self.closures.add(
            Closure(association_id=association_id, first=first, last=last, label=label)
        )
        return closure_read(closure)

    async def delete_closure(self, user: User, association_id: UUID, closure_id: UUID) -> None:
        await self._manager_of(user, association_id)
        closure = await self.closures.get_one_or_none(id=closure_id, association_id=association_id)
        if closure is None:
            raise NotFoundException("Closure not found.")
        await self.closures.delete(closure.id)

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
        if day < date.today():
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
            if not mine:
                raise PermissionDeniedException("Only the registered member can confirm.")
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
