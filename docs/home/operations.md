# Operations

## List my associations

HTTP: `GET /api/associations`.

- [listed] Answers 200 with the associations the signed-in user is a
  member of, with their role and what concerns them there:

  ```json
  [{"id": "5c1e…", "name": "Jardin partagé des Lilas", "slug": "jardin-partage-des-lilas", "role": "manager",
    "upcoming": [
      {"id": "1d3a…", "user_id": "0b6f…", "display_name": "Alice", "status": "confirmed",
       "date": "2026-11-05", "start": "10:00", "end": "13:00"},
      {"id": "48be…", "user_id": "0b6f…", "display_name": "Alice", "status": "proposed",
       "date": "2026-11-14", "start": "10:00", "end": "13:00"}
    ],
    "obsolete": [
      {"id": "9f20…", "user_id": "0b6f…", "display_name": "Alice", "status": "confirmed",
       "date": "2026-11-12", "start": "10:00", "end": "13:00"}
    ],
    "planning_period": {"first": "2026-11-02", "last": "2026-11-25", "registrations": 2}},
   {"id": "9a2d…", "name": "Repair Café Belleville", "slug": "repair-cafe-belleville", "role": "volunteer",
    "upcoming": [], "obsolete": [], "planning_period": null}]
  ```

  Registrations read as in /planning/operations/general, and only the
  signed-in user's show.
- [upcoming] `upcoming` holds the user's registrations dated today or
  later and not obsolete, sorted by date, then start:
  - every proposed one;
  - the confirmed ones up to the later of 27 days after today and,
    when the association has a planning period, its last date.
- [obsolete] `obsolete` holds the user's obsolete registrations dated
  today or later, sorted by date, then start.
- [period] `planning_period` is `null` when the association has none;
  else `registrations` is the user's registration count, as
  /planning/model/registration/count.
