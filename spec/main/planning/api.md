# API

Every endpoint below requires a signed-in member of the association:
401 when signed out, 404 when the association does not exist or the
user is not a member.

## Slots

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

## Closures

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

## GET /api/associations/{id}/schedule?from=…&to=…

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

## POST /api/associations/{id}/registrations

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

## PATCH /api/associations/{id}/registrations/{registration_id}

```http
PATCH /api/associations/5c1e…/registrations/48be…
Content-Type: application/json

{"status": "confirmed"}
```

Returns the registration, as `POST` does.

- R7: The registered user or a manager confirms, and only a `proposed`
  registration that is not obsolete; the registered user or a manager
  cancels a registration that is not cancelled. Anyone else: 403; any
  other change: 409.
- 404 when the registration is not of this association.
