# slot-preferences: members' preferences for slots, and registration counts

Each member states a preference for each slot; managers see and edit
everyone's, and see them, with each member's number of registrations in
the planning period, when proposing an occurrence.

## Data model

- Preference: a member's choice on a slot, at most one per member and
  slot
  - user: a member of the association
  - slot
  - value: `preferred`, `possible` or `unavailable`
  - A member without a preference on a slot has stated none.
  - Deleting a slot deletes its preferences.
- An occurrence's slot is the slot of its weekday, start and end.
- R15: A member's registration count is the number of their
  registrations dated within the planning period, `proposed` or
  `confirmed`, and not obsolete.

## API

### Preferences

```http
GET /api/associations/5c1e…/preferences
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

[{"user_id": "0b6f…", "slot_id": "a41f…", "value": "preferred"},
 {"user_id": "77c0…", "slot_id": "a41f…", "value": "unavailable"}]
```

```http
PUT /api/associations/5c1e…/preferences/a41f…/77c0…
Content-Type: application/json

{"value": "possible"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"user_id": "77c0…", "slot_id": "a41f…", "value": "possible"}
```

- `GET` lists the preferences that are set: all of them for a manager,
  only their own for a volunteer.
- `PUT /api/associations/{id}/preferences/{slot_id}/{user_id}` sets
  the preference, replacing the previous one; `DELETE` on the same
  path: 204, the member has no preference on that slot anymore.
- A volunteer may set or delete only their own: 403 otherwise.
- 404 when the slot is not of this association, or the user is not a
  member.

### GET /api/associations/{id}/registration-counts

```http
HTTP/1.1 200 OK
Content-Type: application/json

[{"user_id": "0b6f…", "count": 2}, {"user_id": "77c0…", "count": 0}]
```

- One entry per member, by R15.
- `null` when there is no planning period.
- Managers only: 403 for a volunteer.

## Screens

### Schedule settings

```
Slots
  Thursday   10:00–13:00   My preference [Preferred ▾]   Delete
  Saturday   10:00–13:00   My preference [—         ▾]   Delete
  Day [Thursday ▾]  From [10:00]  To [13:00]  [Add slot]

Members' preferences
           Thu 10:00–13:00   Sat 10:00–13:00
  Alice    [Preferred ▾]     [—         ▾]
  Bruno    [Possible  ▾]     [Unavailable ▾]
  Chloé    [—         ▾]     [Preferred ▾]
```

- Every member sees "My preference" on each slot. Choosing a value
  saves it at once; "—" deletes it.
- "Members' preferences" is shown to managers only: one row per member,
  one column per slot, each cell a selector that saves at once like
  "My preference".
- Each value has a colour: Preferred green, Possible orange,
  Unavailable red; "—" has none. Selectors show their value's colour.
  (Colours not testable.)
- In French: "Mes préférences", "Préférences des membres", "Préféré",
  "Possible", "Indisponible".

### Schedule

In the occurrence menu, the members' display names that a manager
sees on a free or cancelled occurrence (already specified) now carry
the member's preference and registration count:

```
Sign up
Alice (2)
Bruno (0)
Chloé (1)
```

- Each name has the background colour of the member's preference for
  the occurrence's slot, none when they have stated none (colours not
  testable).
- The name is followed by the member's registration count in
  parentheses; without a planning period, no count is shown.
- The menu is otherwise unchanged: same actions, same order of
  members.
