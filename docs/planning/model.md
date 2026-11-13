# Model

## Time zone

The dates and times of an association's slots, closures, planning
period and registrations are in its timezone. Today is the current
date in the association's timezone.

## Slot

A regular weekly opening of an association.

- `id: /core/model/id`
- `association: /core/model/association`
- `weekday: one of monday, tuesday, wednesday, thursday, friday,
  saturday, sunday`
- `start: time`, `end: time`, times of day, to the minute.
  - [order] Start before end.
- [single] At most one per association, weekday, start and end.

## Closure

A period of whole days when an association is closed.

- `id: /core/model/id`
- `association: /core/model/association`
- `first: date`, `last: date`
  - [order] Last on or after first.
- `label: string`, empty when it has none.

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

An occurrence is identified by its association, date, start and end.
The slot of an occurrence is the slot of its weekday, start and end.

## Preference

A member's choice on a slot; a member without one on a slot has stated
none.

- `user: /core/model/user`
  - [member] A member of the slot's association.
- `slot: /planning/model/slot`
- `value: one of preferred, possible, unavailable`
- [single] At most one per member and slot.

## Absence

A period of whole days when a member is away.

- `id: /core/model/id`
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
- [single] At most one per member and association.

## Registration

The state of a member's commitment on an occurrence.

- `id: /core/model/id`
- `association: /core/model/association`
- `user: /core/model/user`, a member of the association when the
  registration was created.
- `date: date`, `start: time`, `end: time`, those of the occurrence.
- `status: one of proposed, confirmed, cancelled`:
  - `proposed`: asked of the member, not yet confirmed;
  - `confirmed`: the member is committed;
  - `cancelled`: the commitment is withdrawn; the occurrence is free
    again.
- `created_at: /core/model/instant`
- [single] An occurrence holds at most one registration that is not
  cancelled.

A registration that is not cancelled is obsolete when no occurrence
has its date, start and end. A member's registration count is the
number of their registrations dated within the planning period, both
dates included, `proposed` or `confirmed`, and not obsolete.

## ShareLink

An association's read-only link to its Schedule.

- `association: /core/model/association`
- `token: string`, random.
  - [token] Unique.
- [single] At most one per association.
- [lasting] It does not expire (not testable).

## State

With /core/model/state, the software stores:

- `slots: set of /planning/model/slot`
- `closures: set of /planning/model/closure`
- `planning_periods: set of /planning/model/planning-period`
- `preferences: set of /planning/model/preference`
- `absences: set of /planning/model/absence`
- `notes: set of /planning/model/note`
- `registrations: set of /planning/model/registration`
- `share_links: set of /planning/model/sharelink`
