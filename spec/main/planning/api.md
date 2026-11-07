# API

Every endpoint below requires a signed-in member of the association:
401 when signed out, 404 when the association does not exist or the
user is not a member.

## Slots

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

- For managers only: 403 for a volunteer.
- 409 when the association already has that slot.

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

- For managers only: 403 for a volunteer.
- `label` may be omitted or `null`.

## Planning period

```http
PUT /api/associations/5c1e…/planning-period
Content-Type: application/json

{"first": "2026-11-02", "last": "2026-11-25"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"first": "2026-11-02", "last": "2026-11-25"}
```

- It sets the period, replacing the previous one.
- For managers only: 403 for a volunteer.

## Absences

```http
POST /api/associations/5c1e…/absences
Content-Type: application/json

{"first": "2026-11-09", "last": "2026-11-15"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id": "3b8e…", "first": "2026-11-09", "last": "2026-11-15"}
```

- It adds an absence of the user's own.

## Note

```http
PUT /api/associations/5c1e…/note
Content-Type: application/json

{"text": "Always group my registrations in pairs."}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"text": "Always group my registrations in pairs."}
```

- It replaces the user's own note.

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

- A member registering themself signs up, a manager registering
  another member proposes, as on the Schedule (R5, R6). A volunteer
  registering another member: 403.
- 409 when no occurrence has this date, start and end, or it already
  holds a registration that is not cancelled (R4), or the date is
  before today (R6).
- 400 when the user is not a member of the association.
