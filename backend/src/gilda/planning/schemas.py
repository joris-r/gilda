from datetime import date
from typing import Annotated, Literal
from uuid import UUID

import msgspec

Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
Status = Literal["proposed", "confirmed", "cancelled"]
# A time of day to the minute, as "HH:MM".
Clock = Annotated[str, msgspec.Meta(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class SlotCreate(msgspec.Struct):
    weekday: Weekday
    start: Clock
    end: Clock


class SlotRead(msgspec.Struct):
    id: UUID
    weekday: Weekday
    start: str
    end: str


class ClosureCreate(msgspec.Struct):
    first: date
    last: date
    label: str | None = None


class ClosureRead(msgspec.Struct):
    id: UUID
    first: date
    last: date
    label: str | None


class RegistrationCreate(msgspec.Struct):
    user_id: UUID
    date: date
    start: Clock
    end: Clock


class RegistrationUpdate(msgspec.Struct):
    status: Status


class RegistrationRead(msgspec.Struct):
    id: UUID
    user_id: UUID
    display_name: str
    status: Status
    date: date
    start: str
    end: str


class OccurrenceRegistration(msgspec.Struct):
    id: UUID
    user_id: UUID
    display_name: str
    status: Status


class OccurrenceRead(msgspec.Struct):
    date: date
    start: str
    end: str
    registration: OccurrenceRegistration | None


class ScheduleRead(msgspec.Struct):
    occurrences: list[OccurrenceRead]
    obsolete: list[RegistrationRead]
    closures: list[ClosureRead]
