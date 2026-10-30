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
- Occurrence (computed, not stored): a slot on a date of its weekday,
  unless a closure of the association covers that date. It is
  identified by its association, date, start and end.
- Registration: a member on an occurrence
  - id: UUID
  - user: a member of the association
  - date, start, end: those of the occurrence; there is no link to
    the slot
  - status: `proposed`, `confirmed` or `cancelled`
  - R4: An occurrence holds at most one registration that is not
    cancelled.
  - A registration that is not cancelled is obsolete when no
    occurrence has its date, start and end.
