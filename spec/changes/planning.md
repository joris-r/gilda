# planning: volunteers see and fill the schedule

Managers set an association's weekly slots and its closures; members
see the schedule and register on it. A new domain,
`spec/main/planning/`, with `data-model.md`, `api.md` and
`screens.md`, and a new scenario.

## Data model (`planning/data-model.md`)

- Slot: a regular weekly opening of an association
  - id: UUID
  - weekday: `monday` to `sunday`
  - start, end: times of day, to the minute; start before end
  - at most one slot per association, weekday, start and end
- Closure: an association closed for whole days
  - id: UUID
  - first, last: dates; last on or after first
  - label: optional free text
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

## API (`planning/api.md`)

Every endpoint below requires a signed-in member of the association:
401 when signed out, 404 when the association does not exist or the
user is not a member.

### Slots

```http
GET /api/associations/5c1e…/slots
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

[{"id": "a41f…", "weekday": "thursday", "start": "10:00", "end": "13:00"}]
```

```http
POST /api/associations/5c1e…/slots
Content-Type: application/json

{"weekday": "saturday", "start": "10:00", "end": "13:00"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id": "c90b…", "weekday": "saturday", "start": "10:00", "end": "13:00"}
```

- `DELETE /api/associations/{id}/slots/{slot_id}`: 204.
- `POST` and `DELETE` are for managers only: 403 for a volunteer.
- 409 when the association already has that slot.
- Slots are listed by weekday, then start.

### Closures

```http
POST /api/associations/5c1e…/closures
Content-Type: application/json

{"first": "2026-12-24", "last": "2027-01-01", "label": "Fêtes de fin d'année"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id": "e7d2…", "first": "2026-12-24", "last": "2027-01-01", "label": "Fêtes de fin d'année"}
```

- `GET /api/associations/{id}/closures` lists them by first date;
  `DELETE /api/associations/{id}/closures/{closure_id}`: 204.
- `POST` and `DELETE` are for managers only: 403 for a volunteer.
- `label` may be omitted or `null`.

### GET /api/associations/{id}/schedule?from=…&to=…

The occurrences, obsolete registrations and closures between two
dates, both included.

```http
GET /api/associations/5c1e…/schedule?from=2026-11-02&to=2026-11-15
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "occurrences": [
    {"date": "2026-11-05", "start": "10:00", "end": "13:00",
     "registration": {"id": "1d3a…", "user_id": "77c0…", "display_name": "Chloé", "status": "confirmed"}},
    {"date": "2026-11-07", "start": "10:00", "end": "13:00",
     "registration": {"id": "48be…", "user_id": "0b6f…", "display_name": "Alice", "status": "cancelled"}},
    {"date": "2026-11-12", "start": "10:00", "end": "13:00", "registration": null}
  ],
  "obsolete": [
    {"id": "9f20…", "user_id": "a3c1…", "display_name": "David", "status": "proposed",
     "date": "2026-11-14", "start": "10:00", "end": "13:00"}
  ],
  "closures": [
    {"id": "e7d2…", "first": "2026-11-14", "last": "2026-11-14", "label": "Fête du quartier"}
  ]
}
```

- An occurrence's `registration` is the one that is not cancelled;
  else the latest cancelled one; else `null`.
- `closures` holds those that cover at least one date of the range.
- Occurrences and obsolete registrations are sorted by date, then
  start.

### POST /api/associations/{id}/registrations

```http
POST /api/associations/5c1e…/registrations
Content-Type: application/json

{"user_id": "77c0…", "date": "2026-11-05", "start": "10:00", "end": "13:00"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id": "1d3a…", "user_id": "77c0…", "display_name": "Chloé", "status": "confirmed",
 "date": "2026-11-05", "start": "10:00", "end": "13:00"}
```

- R5: A member registering themself gets `confirmed`; a manager
  registering another member gets `proposed`. A volunteer registering
  another member: 403.
- 409 when no occurrence has this date, start and end, or it already
  holds a registration that is not cancelled (R4).
- 400 when the user is not a member of the association.
- R6: 409 when the date is before today.

### PATCH /api/associations/{id}/registrations/{registration_id}

```http
PATCH /api/associations/5c1e…/registrations/48be…
Content-Type: application/json

{"status": "confirmed"}
```

Returns the registration, as `POST` does.

- R7: Only the registered user confirms, and only a `proposed`
  registration that is not obsolete; the registered user or a manager
  cancels a registration that is not cancelled. Anyone else: 403; any
  other change: 409.
- 404 when the registration is not of this association.

## Screens (`planning/screens.md`)

The Association page gets two links under the name: "Schedule" and
"Opening hours".

### `/associations/{id}/opening`: Opening hours

```
← Jardin partagé
Opening hours

Slots
  Thursday   10:00–13:00   Delete
  Saturday   10:00–13:00   Delete
  Day [Thursday ▾]  From [10:00]  To [13:00]  [Add slot]

Closures
  Sat 14 Nov 2026                  Fête du quartier   Delete
  Thu 24 Dec 2026 – Fri 1 Jan 2027  Fêtes de fin d'année   Delete
  From [    ]  To [    ]  Label [          ]  [Add closure]
```

- A volunteer sees the lists, without Delete and without the forms.

### `/associations/{id}/schedule`: Schedule

Wide screen:

```
← Jardin partagé
Schedule

Week 43 · 19 – 25 Oct
       Thu 22 Oct        Sat 24 Oct
10h  ┌──────────────┐  ┌──────────────┐
     │10–13 Alice   │  │10–13 nobody  │
13h  └──────────────┘  └──────────────┘

── Today · Wednesday 28 October 2026 ───────────────────────

Week 44 · 26 Oct – 1 Nov
       Thu 29 Oct        Sat 31 Oct
10h  ┌──────────────┐  ┌──────────────┐
     │10–13 Chloé   │  │10–13 Bruno ? │
13h  └──────────────┘  └──────────────┘

Week 45 · 2 – 8 Nov
       Thu 5 Nov         Sat 7 Nov
10h  ┌──────────────┐  ┌──────────────┐
     │10–13 ~~Alice~~│  │   Closed     │
13h  └──────────────┘  │Fête du quart.│
                        └──────────────┘
…
[More weeks]
```

Narrow screen, same weeks:

```
Week 44 · 26 Oct – 1 Nov
         10h        13h
Thu 29   [Chloé      ]
Sat 31   [Bruno ?    ]
```

- It opens on the week before the current one and shows six weeks;
  "More weeks", at the end, adds four more.
- Each week has one column per weekday on which an occurrence of the
  shown weeks falls. Time runs down, on the same scale in every week,
  from the earliest start to the latest end of the shown occurrences,
  rounded to whole hours: an occurrence is placed and sized by its
  start and end. Occurrences of a day that overlap sit side by side.
  (Placement and sizes not testable.)
- On a narrow screen, each week has one row per such weekday, and time
  runs from left to right. (Not testable.)
- A line marked with today's date separates the past weeks from the
  current week; the days before today look different from the others
  (look of past days not testable).
- An occurrence shows its times and its registration's display name:
  green when confirmed; orange with "?" when proposed; red when it has
  no registration ("nobody") or a cancelled one, whose name is struck.
  (Colours not testable.)
- An obsolete registration is placed like an occurrence, by its date,
  start and end, marked "obsolete".
- A day covered by a closure shows "Closed" and the closure's label.
- Clicking an occurrence or an obsolete registration, from today on,
  opens a menu on it:
  - free or cancelled: "Sign up"; for a manager, also the members'
    display names, each proposing the occurrence to that member;
  - the user's own proposed registration: "Confirm";
  - the user's own registration, or any for a manager: "Cancel
    registration…", which asks "Cancel this registration? [Yes,
    cancel] Keep it" before cancelling.

## Scenarios (`scenarios.md`)

New scenario:

### The schedule is filled

1. Alice, a manager of Jardin partagé, adds the slots Thursday 10–13
   and Saturday 10–13, and a closure on the Saturday of the week after
   next, labelled "Fête du quartier".
2. Chloé, a volunteer, opens the Schedule. That Saturday shows
   "Closed" and "Fête du quartier". She signs up for next week's
   Thursday 10–13: her name shows, green.
3. Alice proposes next week's Saturday 10–13 to Chloé: it shows
   orange, with "?".
4. Chloé confirms it: it turns green. She cancels her Thursday: her
   name shows struck, red.
5. David, a volunteer, signs up for that Thursday: his name replaces
   Chloé's, green.
