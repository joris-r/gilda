# Model

## Time zone

- [local] The dates and times of an association's slots, closures,
  planning period and registrations are in its timezone.
- [today] Today is the current date in the association's timezone.

## Slot

A regular weekly opening of an association.

- `id: UUID`
- `association: /core/model/association`
- `weekday: string`, `monday` to `sunday`.
- `start: time`, `end: time`, times of day, to the minute.
  - [order] Start before end.
- [single] At most one per association, weekday, start and end.

## Closure

A period of whole days when an association is closed.

- `id: UUID`
- `association: /core/model/association`
- `first: date`, `last: date`
  - [order] Last on or after first.
- `label: string`, optional.

## Planning period

The dates the managers ask the members to fill.

- `association: /core/model/association`
- `first: date`, `last: date`
  - [order] Last on or after first.
- [single] At most one per association.

## Occurrence

Not stored: a slot on a date of its weekday, unless a closure of the
association covers that date.

- `association: /core/model/association`
- `date: date`
- `start: time`, `end: time`
- [identity] An occurrence is identified by its association, date,
  start and end.
- [slot] The slot of an occurrence is the slot of its weekday, start
  and end.

## Preference

A member's choice on a slot; a member without one on a slot has stated
none.

- `user: /core/model/user`
  - [member] A member of the slot's association.
- `slot: /planning/model/slot`
- `value: string`, `preferred`, `possible` or `unavailable`.
- [single] At most one per member and slot.

## Absence

A period of whole days when a member is away.

- `id: UUID`
- `association: /core/model/association`
- `user: /core/model/user`
  - [member] A member of the association.
- `first: date`, `last: date`
  - [order] Last on or after first.

## Note

A member's standing instructions for the managers.

- `association: /core/model/association`
- `user: /core/model/user`
  - [member] A member of the association.
- `text: string`, empty by default.
- [single] At most one per member.

## Registration

The state of a member's commitment on an occurrence.

- `id: UUID`
- `association: /core/model/association`
- `user: /core/model/user`
  - [member] A member of the association when the registration was
    created.
- `date: date`, `start: time`, `end: time`, those of the occurrence.
- `status: string`:
  - `proposed`: asked of the member, not yet confirmed;
  - `confirmed`: the member is committed;
  - `cancelled`: the commitment is withdrawn; the occurrence is free
    again.
- [single] An occurrence holds at most one registration that is not
  cancelled.
- [obsolete] A registration that is not cancelled is obsolete when no
  occurrence has its date, start and end.
- [count] A member's registration count is the number of their
  registrations dated within the planning period, both dates included,
  `proposed` or `confirmed`, and not obsolete.

## ShareLink

An association's read-only link to its Schedule.

- `association: /core/model/association`
- `token: string`, random.
  - [token] Unique.
- [single] At most one per association.
- [lasting] It does not expire.
