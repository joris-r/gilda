# UI

## My associations

At `/`, signed in; mockups in `design/my-associations.md`. It shows
/home/operations/list-my-associations.

Shows:
- [list] Each association: its name, leading to its Schedule, and the
  user's role there, "MANAGER" or "VOLUNTEER"; then its summary.
- [none] With no association: "You are not a member of any association
  yet."
- [new] Below the list, "+ New association", leading to
  `/association/new`.

The summary of an association shows:
- [obsolete] first, its obsolete registrations, each followed by
  "this slot no longer takes place." and "OK";
- [upcoming] then its upcoming registrations; a proposed one is marked
  "?" and has "Confirm";
- [registration] each registration shows its date and times, then its
  display name, then its action;
- [no-registration] when the association has a planning period that
  ends today or later and the user's registration count in it is 0:
  "No registration yet for the planning period, <dates>." and "Choose
  your slots";
- [no-upcoming] otherwise, with no upcoming registration: "No upcoming
  registration."
- [dates] The period's dates read "2–25 Nov" within a month, "28 Oct
  – 25 Nov" across months, and with years when they differ: "28 Dec
  2026 – 8 Jan 2027".

Actions:
- [confirm] "Confirm" runs /planning/operations/change-registration on
  the registration, confirming.
- [acknowledge] "OK" runs /planning/operations/change-registration on
  the registration, cancelling; it then no longer shows.
- [choose] "Choose your slots" leads to the association's Schedule.
