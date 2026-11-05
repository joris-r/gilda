# Data model: planning

## Scope: Calendar

### Entity: Slot

A regular weekly opening of an association, at most one per association,
weekday, start and end.

- Fields
  - id: UUID
  - association
  - weekday: `monday` to `sunday`
  - start, end: times of day, to the minute; start before end

### Entity: Closure

A period of whole days when an association is closed.

- Fields
  - id: UUID
  - association
  - first, last: dates; last on or after first
  - label: optional free text

### Entity: Planning period

The dates the managers ask the members to fill, at most one per
association.

- Fields
  - association
  - first, last: dates; last on or after first

### Entity: Occurrence

Computed, not stored: a slot on a date of its weekday, unless a closure
of the association covers that date.

- Fields
  - association
  - date
  - start, end
- Rules
  - An occurrence is identified by its association, date, start and end.
  - The slot of an occurrence is the slot of its weekday, start and end.

## Scope: Member availability

### Entity: Preference

A member's choice on a slot, at most one per member and slot.

- Fields
  - user: a member of the slot's association
  - slot
  - value: `preferred`, `possible` or `unavailable`
- Rules
  - A member without a preference on a slot has stated none.
  - Deleting a slot deletes its preferences; editing it keeps them.

### Entity: Absence

A period of whole days when a member is away.

- Fields
  - id: UUID
  - association
  - user: a member of the association
  - first, last: dates; last on or after first

### Entity: Note

A member's standing instructions for the managers, at most one per
member.

- Fields
  - association
  - user: a member of the association
  - text: free text; empty by default

## Scope: Registrations

### Entity: Registration

A member on an occurrence.

- Fields
  - id: UUID
  - association
  - user: a member of the association when the registration was created
  - date, start, end: those of the occurrence; there is no link to the
    slot
  - status: `proposed`, `confirmed` or `cancelled`
- Rules
  - R4: An occurrence holds at most one registration that is not
    cancelled.
  - A registration that is not cancelled is obsolete when no occurrence
    has its date, start and end.
  - R15: A member's registration count is the number of their
    registrations dated within the planning period, `proposed` or
    `confirmed`, and not obsolete.

## Scope: Sharing

### Entity: ShareLink

An association's read-only link to its Schedule, at most one per
association.

- Fields
  - association
  - token: random, unique
- Rules
  - A share link does not expire.
  - R33: Creating a share link replaces the previous one; revoking it
    deletes it. A replaced or revoked link no longer shows the Schedule.

## General rules

- R28: When a user's membership ends, their registrations in the
  association dated today or later and not cancelled become cancelled,
  and their preferences, absences and note there are deleted. Their
  other registrations stay, with their display name.
- The dates and times of an association's slots, closures, planning
  period and registrations are in its timezone.
- R11: Today, wherever the specification refers to it, is the current
  date in the association's timezone.
