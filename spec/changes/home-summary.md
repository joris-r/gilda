# Home summary

On My associations, each association shows what concerns the signed-in
user: their upcoming registrations, proposed ones to confirm, and a
reminder when they have nothing in the planning period.

## API

### GET /api/associations

Replaces the example of `GET /api/associations`:

```http
HTTP/1.1 200 OK
Content-Type: application/json

[{"id": "5c1e…", "name": "Jardin partagé des Lilas", "role": "manager",
  "upcoming": [
    {"id": "1d3a…", "user_id": "0b6f…", "display_name": "Alice", "status": "confirmed",
     "date": "2026-11-05", "start": "10:00", "end": "13:00"},
    {"id": "48be…", "user_id": "0b6f…", "display_name": "Alice", "status": "proposed",
     "date": "2026-11-14", "start": "10:00", "end": "13:00"}
  ],
  "planning_period": {"first": "2026-11-02", "last": "2026-11-25", "registrations": 2}},
 {"id": "9a2d…", "name": "Repair Café Belleville", "role": "volunteer",
  "upcoming": [], "planning_period": null}]
```

- Registrations are shown as `POST /api/associations/{id}/registrations`
  returns them, and only the signed-in user's that are not obsolete.
- R12: `upcoming` holds the user's registrations dated today or later,
  sorted by date, then start:
  - every proposed one;
  - the confirmed ones up to the planning period's last date, when the
    association has a period that ends today or later; else up to 27
    days after today.
- R13: `planning_period` is `null` when the association has none; else
  `registrations` counts the user's confirmed and proposed
  registrations dated within the period, both dates included.

## Screens

### `/`, signed in: My associations

Replaces the drawing of My associations:

```
(logo)  My associations                                    Alice ▾

                                                              [+]
  Jardin partagé des Lilas                 MANAGER
    Thu 5 Nov, 10:00–13:00
    Sat 14 Nov, 10:00–13:00 ?  [Confirm]

  Repair Café Belleville                 VOLUNTEER
    No registration yet for the planning period, 2–25 Nov.
    Choose your slots

  Atelier vélo                           VOLUNTEER
    No upcoming registration.
```

- Each association lists its `upcoming` registrations; a proposed one
  is marked "?" and has "Confirm", which confirms it.
- R14: When the association has a planning period that ends today or
  later and the user has no registration in it (`registrations` is 0),
  the summary shows "No registration yet for the planning period,"
  with its dates, and "Choose your slots", which leads to the
  association's Schedule.
- Otherwise, with no upcoming registration: "No upcoming
  registration."
- The period's dates read as "2–25 Nov" within a month, "28 Oct – 25
  Nov" across months, and with years when they differ: "28 Dec 2026 –
  8 Jan 2027".

In French, e.g.:

```
Mes associations
  Jardin partagé des Lilas             RESPONSABLE
    jeu. 5 nov., 10:00–13:00
    sam. 14 nov., 10:00–13:00 ?  [Confirmer]
  Repair Café Belleville                  BÉNÉVOLE
    Aucune inscription pour la période de planning, 2–25 nov.
    Choisir mes créneaux
  Atelier vélo                            BÉNÉVOLE
    Aucune inscription à venir.
```
