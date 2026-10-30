# Association timezone

An association has a timezone; the server and the schedule both count
today in it.

## Data model

- Association
  - timezone: an IANA timezone name; always `Europe/Paris`
  - The dates and times of its slots, closures, planning period and
    registrations are in this timezone.

## API

### GET /api/associations/{id}

Adds `timezone`:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "5c1e…",
  "name": "Jardin partagé des Lilas",
  "timezone": "Europe/Paris",
  "role": "manager",
  "members": […]
}
```

## Behavior

- R11: Today, wherever the specification refers to it, is the current
  date in the association's timezone. This covers R6, and on the
  Schedule the today line, the days before today, and the menus opened
  from today on.
