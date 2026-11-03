# Data model

- Slot: a regular weekly opening of an association
  - id: UUID
  - weekday: `monday` to `sunday`
  - start, end: times of day, to the minute; start before end
  - at most one slot per association, weekday, start and end
- Closure: an association closed for whole days
  - id: UUID
  - first, last: dates; last on or after first
  - label: optional free text
- Planning period: the dates the managers ask the members to fill
  - first, last: dates; last on or after first
  - at most one per association
- Preference: a member's choice on a slot, at most one per member and
  slot
  - user: a member of the association
  - slot
  - value: `preferred`, `possible` or `unavailable`
  - A member without a preference on a slot has stated none.
  - Deleting a slot deletes its preferences; editing it keeps them.
- Absence: a member away for whole days
  - id: UUID
  - user: a member of the association
  - first, last: dates; last on or after first
- Note: a member's standing instructions for the managers, at most one
  per member
  - user: a member of the association
  - text: free text; empty by default
- ShareLink: an association's read-only link to its Schedule, at most
  one per association
  - token: random, unique
  - It does not expire.
  - R33: Creating a share link replaces the previous one; revoking it
    deletes it. A replaced or revoked link no longer shows the
    Schedule.
- Occurrence (computed, not stored): a slot on a date of its weekday,
  unless a closure of the association covers that date. It is
  identified by its association, date, start and end. Its slot is the
  slot of its weekday, start and end.
- Registration: a member on an occurrence
  - id: UUID
  - user: a member of the association when it was created
  - date, start, end: those of the occurrence; there is no link to
    the slot
  - status: `proposed`, `confirmed` or `cancelled`
  - R4: An occurrence holds at most one registration that is not
    cancelled.
  - A registration that is not cancelled is obsolete when no
    occurrence has its date, start and end.
- R15: A member's registration count is the number of their
  registrations dated within the planning period, `proposed` or
  `confirmed`, and not obsolete.
- R28: When a user's membership ends, their registrations in the
  association dated today or later and not cancelled become cancelled,
  and their preferences, absences and note there are deleted. Their
  other registrations stay, with their display name.
- R11: Today, wherever the specification refers to it, is the current
  date in the association's timezone.
