# UI

## Schedule settings

× - [set-preference] A cell of "Members' preferences" saves at once, as
×   /planning/ui/my-availability/set, for the row's member and the
×   column's slot.
- [set-preference] A cell of "Members' preferences" saves at once, as
  /planning/ui/my-availability/set, for the row's member and the
  column's slot, and shows its value as
  /planning/ui/my-availability/saved-value.

## My availability

  the value; "—" runs /planning/operations/delete-preference. …
  - [saved-value] While a save of the selector runs, it shows the last
    value chosen. Once none runs, it shows the value of the save that
    succeeded last, in the order the answers came, or else the value
    it opened with: a refused or failed save does not change it.

## Schedule

  date as well. …
  - [menu-past] Clicking an occurrence or an obsolete registration
    that the Schedule still shows from today on, though its date is
    now before today: the menu opens with only "This day is past.",
    and the Schedule shows its weeks again at once, as
    /planning/ui/schedule/new-day.
- [past] In the Occurrence menu, /planning/operations/register/past
  and /planning/operations/change-registration/past: "This day is
  past.", in the menu, or in its confirmation for Cancel registration;
  the Schedule shows its weeks again at once, as
  /planning/ui/schedule/new-day.
- [new-day] Once today changes while the Schedule is open, it shows
  the same weeks again, More weeks included, from
  /planning/operations/get-schedule with their dates, without a
  reload: its Today line, its days before today and the occurrences
  that open the menu follow the new today. It does so within a minute
  of the change, or of the screen showing again when it was hidden
  then. An open menu or confirmation stays open. When More weeks runs
  at the same time, which weeks it then shows is left free.
  - [new-day-signed-out] Refused as
    /core/operations/general/signed-out: as /core/ui/access/action.
  - [new-day-failed] Otherwise refused, or failing: the Schedule stays
    as it was, with no message.

## Occurrence menu

  - [order] The names are sorted by the member's preference for the …
    registrations, as /planning/model/registration defines the count; …
×     then by
×     display name.
    then by display name, as /ui/name-order.
  slot in the meantime." …
- [fresh] The message of a refused or failed try shows in the menu
  until the next try or the menu closes: opened again, the menu shows
  no message of an earlier try.

## Shared schedule

  no menu. …
- [new-day] Once today changes while it is open, it shows its weeks
  again as /planning/ui/schedule/new-day, from
  /planning/operations/get-shared-schedule with the token and their
  dates; refused, the link being unknown, replaced or revoked, or
  failing, it stays as it was, with no message.
