# Operations

## General

/core/operations/general applies. A registration reads
`{"id": "1d3a…", "user_id": "77c0…", "display_name": "Chloé",
"status": "confirmed", "date": "2026-11-05", "start": "10:00", "end":
"13:00"}`.

- [member] Every operation below but Get shared association and Get
  shared schedule requires a signed-in member of the association, as
  /core/operations/general/signed-out and
  /core/operations/general/unknown-association.

## List slots

HTTP: `GET /api/associations/<id>/slots`.

- [listed] Answers 200 with the association's slots, by weekday, then
  start: `[{"id": "a41f…", "weekday": "thursday", "start": "10:00",
  "end": "13:00"}]`.

## Add slot

HTTP: `POST /api/associations/<id>/slots` with `{"weekday":
"saturday", "start": "10:00", "end": "13:00"}`.

- [added] A new slot: it is stored; answers 201 with the slot.
- [exists] The association already has that slot: refused, 409.
- [order] Start not before end: refused, 400.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Edit slot

HTTP: `PUT /api/associations/<id>/slots/<slot_id>`, with the body of
/planning/operations/add-slot.

- [edited] The slot takes the weekday, start and end, and keeps its
  preferences; answers 200 with the slot.
- [exists] Another slot of the association has them: refused, 409.
- [order] Start not before end: refused, 400.
- [unknown] The slot is not of this association: refused, 404.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Delete slot

HTTP: `DELETE /api/associations/<id>/slots/<slot_id>`.

- [deleted] The slot and its preferences are deleted; answers 204.
- [unknown] The slot is not of this association: refused, 404.
- [volunteer] Signed-in user a volunteer: refused, 403.

## List closures

HTTP: `GET /api/associations/<id>/closures`.

- [listed] Answers 200 with the association's closures, by first
  date.

## Add closure

HTTP: `POST /api/associations/<id>/closures` with `{"first":
"2026-12-24", "last": "2027-01-01", "label": "Fêtes de fin
d'année"}`.

- [added] The closure is stored; answers 201 with `{"id": "e7d2…",
  "first": "2026-12-24", "last": "2027-01-01", "label": "Fêtes de fin
  d'année"}`.
- [no-label] `label` may be omitted or `null`.
- [order] Last before first: refused, 400.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Edit closure

HTTP: `PUT /api/associations/<id>/closures/<closure_id>`, with the
body of /planning/operations/add-closure.

- [edited] The closure takes the dates and label; answers 200 with
  the closure.
- [order] Last before first: refused, 400.
- [unknown] The closure is not of this association: refused, 404.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Delete closure

HTTP: `DELETE /api/associations/<id>/closures/<closure_id>`.

- [deleted] The closure is deleted; answers 204.
- [unknown] The closure is not of this association: refused, 404.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Get planning period

HTTP: `GET /api/associations/<id>/planning-period`.

- [period] Answers 200 with `{"first": "2026-11-02", "last":
  "2026-11-25"}`, or `null` when there is none.

## Set planning period

HTTP: `PUT /api/associations/<id>/planning-period` with `{"first":
"2026-11-02", "last": "2026-11-25"}`.

- [set] The period is set, replacing the previous one; answers 200
  with it.
- [order] Last before first: refused, 400.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Clear planning period

HTTP: `DELETE /api/associations/<id>/planning-period`.

- [cleared] There is no period anymore; answers 204.
- [volunteer] Signed-in user a volunteer: refused, 403.

## List preferences

HTTP: `GET /api/associations/<id>/preferences`.

- [manager] To a manager: answers 200 with every preference that is
  set, `[{"user_id": "0b6f…", "slot_id": "a41f…", "value":
  "preferred"}]`.
- [volunteer] To a volunteer: only their own.

## Set preference

HTTP: `PUT /api/associations/<id>/preferences/<slot_id>/<user_id>`
with `{"value": "possible"}`.

- [set] The member's preference on the slot is the value, replacing
  the previous one, even when several requests for the same member
  and slot run at once; answers 200 with the preference.
- [other] A volunteer, for another member: refused, 403.
- [unknown] The slot is not of this association, or the user not a
  member: refused, 404.

## Delete preference

HTTP: `DELETE /api/associations/<id>/preferences/<slot_id>/<user_id>`.

- [deleted] The member has no preference on the slot anymore; answers
  204.
- [other] A volunteer, for another member: refused, 403.
- [unknown] The slot is not of this association, or the user not a
  member: refused, 404.

## List absences

HTTP: `GET /api/associations/<id>/absences`.

- [listed] Answers 200 with the user's own absences in the
  association, by first date.

## Add absence

HTTP: `POST /api/associations/<id>/absences` with `{"first":
"2026-11-09", "last": "2026-11-15"}`.

- [added] The absence is stored as the user's; answers 201 with
  `{"id": "3b8e…", "first": "2026-11-09", "last": "2026-11-15"}`.
- [order] Last before first: refused, 400.

## Edit absence

HTTP: `PUT /api/associations/<id>/absences/<absence_id>`, with the
body of /planning/operations/add-absence.

- [edited] The absence takes the dates; answers 200 with it.
- [order] Last before first: refused, 400.
- [unknown] The absence is not the user's in this association:
  refused, 404.

## Delete absence

HTTP: `DELETE /api/associations/<id>/absences/<absence_id>`.

- [deleted] The absence is deleted; answers 204.
- [unknown] The absence is not the user's in this association:
  refused, 404.

## List member absences

HTTP: `GET /api/associations/<id>/member-absences`.

- [listed] Answers 200 with the absences of all members, by first
  date: `[{"id": "3b8e…", "user_id": "0b6f…", "first": "2026-11-09",
  "last": "2026-11-15"}]`.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Get note

HTTP: `GET /api/associations/<id>/note`.

- [note] Answers 200 with the user's own note, `{"text": "Always group
  my registrations in pairs."}`; `""` when never set.

## Set note

HTTP: `PUT /api/associations/<id>/note` with `{"text": "…"}`.

- [set] The user's note is the text, replacing the previous one;
  answers 200 with it.

## List notes

HTTP: `GET /api/associations/<id>/notes`.

- [listed] Answers 200 with one entry per member: `[{"user_id":
  "0b6f…", "text": "Always group my registrations in pairs."},
  {"user_id": "77c0…", "text": ""}]`.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Get registration counts

HTTP: `GET /api/associations/<id>/registration-counts`.

- [counts] Answers 200 with one entry per member, their registration
  count as /planning/model/registration/count: `[{"user_id": "0b6f…",
  "count": 2}]`.
- [no-period] No planning period: answers 200 with `null`.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Get schedule

HTTP: `GET /api/associations/<id>/schedule?from=<date>&to=<date>`.

- [range] Answers 200 with the occurrences, obsolete registrations and
  closures between the two dates, both included:

  ```json
  {
    "from": "2026-11-02",
    "to": "2026-11-15",
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
- [default] Without `from` and `to`: the range starts on the Monday of
  the week before today's and spans six weeks, and more if needed to
  reach the end of the week after the one that holds the planning
  period's last date.
- [one-bound] Only one of `from` and `to`: refused, 400.
- [registration] An occurrence's `registration` is the one that is not
  cancelled; else the latest cancelled one; else `null`.
- [closures] `closures` holds those that cover at least one date of
  the range.
- [order] Occurrences and obsolete registrations are sorted by date,
  then start.

## Register

HTTP: `POST /api/associations/<id>/registrations` with `{"user_id":
"77c0…", "date": "2026-11-05", "start": "10:00", "end": "13:00"}`.

- [self] A member registering themself: the registration is stored,
  `confirmed`; answers 201 with it.
- [proposed] A manager registering another member: the registration
  is stored, `proposed`; answers 201 with it.
- [other] A volunteer registering another member: refused, 403.
- [no-occurrence] No occurrence has this date, start and end: refused,
  409.
- [taken] The occurrence already holds a registration that is not
  cancelled: refused, 409.
- [non-member] The user is not a member of the association: refused,
  400.
- [past] The date is before today: refused, 409.

## Change registration

HTTP: `PATCH /api/associations/<id>/registrations/<registration_id>`
with `{"status": "confirmed"}` or `{"status": "cancelled"}`.

- [confirm] The registered user or a manager, confirming a `proposed`
  registration that is not obsolete: it becomes `confirmed`; answers
  200 with it.
- [cancel] The registered user or a manager, cancelling a registration
  that is not cancelled: it becomes `cancelled`; answers 200 with it.
- [forbidden] Anyone else: refused, 403.
- [other] Any other change: refused, 409.
- [unknown] The registration is not of this association: refused, 404.

## Create share link

HTTP: `POST /api/associations/<id>/share-link`.

- [created] A ShareLink is created, replacing the previous one; answers 201 with `{"token": "Hq3v…"}`.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Get share link

HTTP: `GET /api/associations/<id>/share-link`.

- [link] Answers 200 with the ShareLink, as
  /planning/operations/create-share-link/created, or `null` when there
  is none.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Revoke share link

HTTP: `DELETE /api/associations/<id>/share-link`.

- [revoked] The ShareLink, if any, is deleted; answers 204.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Get shared association

HTTP: `GET /api/shared/<token>`, signed in or not.

- [shared] Answers 200 with `{"name": "Jardin partagé des Lilas",
  "timezone": "Europe/Paris", "planning_period": {"first":
  "2026-11-02", "last": "2026-11-25"}}`; `planning_period` is `null`
  when there is none.
- [unknown] No ShareLink has this token: refused, 404.

## Get shared schedule

HTTP: `GET /api/shared/<token>/schedule?from=<date>&to=<date>`,
signed in or not.

- [schedule] Answers as /planning/operations/get-schedule for the
  association, with the same parameters.
- [unknown] No ShareLink has this token: refused, 404.

## Remove member

Extends /core/operations/remove-member.

- [planning] When the membership ends:
  - the member's registrations in the association dated today or
    later and not cancelled become cancelled;
  - their preferences, absences and note there are deleted;
  - their other registrations stay, with their display name.

## Delete account

Extends /core/operations/delete-account.

- [planning] Each membership that ends does so as
  /planning/operations/remove-member/planning.

## Delete association

Extends /core/operations/delete-association.

- [planning] Its slots, closures, planning period, preferences,
  absences, notes, share link and registrations are erased.
