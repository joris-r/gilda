# Planning period

Managers set the planning period of an association; the schedule shows
it between two lines and greys the occurrences after it.

## Data model

- Planning period: the dates the managers ask the members to fill
  - first, last: dates; last on or after first
  - at most one per association

## API

### `/api/associations/{id}/planning-period`

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

- `PUT` sets the period, replacing the previous one.
- `GET` returns it; `null` when there is none.
- `DELETE`: 204; there is no period anymore.
- `PUT` and `DELETE` are for managers only: 403 for a volunteer.

## Screens

### `/associations/{id}/opening`: Opening hours

Adds, after Closures:

```
Planning period
  From [2026-11-02]  To [2026-11-25]  [Save]  [Clear]
```

- A volunteer sees the period, or "None", without the form.

### `/associations/{id}/schedule`: Schedule

Adds, when a period is set:

```
── Today · Wednesday 28 October 2026 ───────────────────────

Week 44 · 26 Oct – 1 Nov
…

── Planning period · from Monday 2 November 2026 ───────────

Week 45 · 2 – 8 Nov
…
Week 48 · 23 – 29 Nov
       Thu 26 Nov        Sat 28 Nov
       (greyed)          (greyed)

── End of planning period · Wednesday 25 November 2026 ─────

Week 49 · 30 Nov – 6 Dec      (greyed)
…
```

- A line marked with the first date sits just before the week that
  holds it; a line marked with the last date, just after the week that
  holds it. When the first line and the today line fall at the same
  place, the today line comes first.
- Occurrences and obsolete registrations after the last date are
  greyed, and keep their menu. (Look not testable.)
