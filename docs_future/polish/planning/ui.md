# UI

## Schedule settings

× - [closures] CLOSURES: each closure's dates and label, by first date,
×   or "None".
- [closures] CLOSURES: the closures ending today or later, each with
  its dates and label, by first date, or "None"; earlier ones do not
  show.
  /planning/operations/set-planning-period with the fields. …
  - [period-order] /planning/operations/set-planning-period/order: "The
    end date can't be before the start date."
  To, Label, [Add closure]; it runs /planning/operations/add-closure …
  with the fields. …
  - [closure-order] /planning/operations/add-closure/order: "The end
    date can't be before the start date."
  - [closure-past] /planning/operations/add-closure/past: "The end date
    can't be before today."
  - [closure-warning] The dialog shows "Registrations on its dates,
    from today on, become obsolete."
  closure", filled with the closure, with [Save]; it runs …
  /planning/operations/edit-closure for it, with the fields. …
  - [edit-closure-order] /planning/operations/edit-closure/order: "The
    end date can't be before the start date."
  - [edit-closure-past] /planning/operations/edit-closure/past: "The
    end date can't be before today."
  - [edit-closure-warning] The dialog shows "Registrations on its new
    dates, from today on, become obsolete; those on the dates it no
    longer covers may stop being obsolete."
  with [Delete], which runs /planning/operations/delete-closure for …
  it. …
  - [delete-closure-warning] The question goes on with "Registrations
    on its dates, from today on, may stop being obsolete."
  - [exists] /planning/operations/add-slot/exists: "This slot already …
    exists." …
  - [order] /planning/operations/add-slot/order: "The end time must be
    after the start time."
  - [edit-exists] /planning/operations/edit-slot/exists: "This slot …
    already exists." …
  - [edit-order] /planning/operations/edit-slot/order: "The end time
    must be after the start time."
  - [edit-warning] The dialog shows "Changing the day or times makes
    its registrations from today on obsolete."
  /planning/operations/delete-slot for it. …
  - [delete-slot-warning] The question goes on with "Its registrations
    from today on become obsolete, and the members' preferences on it
    are deleted."
× - [copy] "Copy" copies the link and shows "Link copied."
- [copy] "Copy" copies the link and shows "Link copied.", in place of
  the message of an earlier Copy.
  - [copy-failed] When the browser does not copy it: "The link
    couldn't be copied. Select it to copy it." instead.
× - [set-preference] A cell of "Members' preferences" saves at once, as
×   /planning/ui/my-availability/set, for the row's member and the
×   column's slot.
- [set-preference] A cell of "Members' preferences" saves at once, as
  /planning/ui/my-availability/set, for the row's member and the
  column's slot, and shows its value as
  /planning/ui/my-availability/saved-value.
- [preferences-again] When the screen, opened by a manager, shows
  again after being hidden, once no save of "Members' preferences"
  runs, the first that holds:
  1. [preferences-again-signed-out] Signed out by then: it leads to
     Sign in.
  2. [preferences-again-failed] The user no longer a manager of the
     association, or failing: the screen stays as it was, with no
     message.
  3. [preferences-again-shown] Otherwise: "Members' preferences" shows
     again as it now is, its members, slots and values, without a
     reload; each selector then shows its value as
     /planning/ui/my-availability/saved-value, with the value it
     showed again with for the value it opened with.

## My availability

  the value; "—" runs /planning/operations/delete-preference. …
  - [saved-value] While a save of the selector runs, it shows the last
    value chosen. Once none runs, it shows the value of the save that
    succeeded last, in the order the answers came, or else the value
    it opened with: a refused or failed save does not change it.
  From, To, [Add absence]; it runs /planning/operations/add-absence …
  with the fields. …
  - [absence-order] /planning/operations/add-absence/order: "The end
    date can't be before the start date."
  - [absence-past] /planning/operations/add-absence/past: "The end date
    can't be before today."
  - [absence-overlap] /planning/operations/add-absence/overlap: "This
    absence overlaps another one."
  absence", filled with it, with [Save]; it runs …
  /planning/operations/edit-absence for it, with the fields. …
  - [edit-absence-order] /planning/operations/edit-absence/order: "The
    end date can't be before the start date."
  - [edit-absence-past] /planning/operations/edit-absence/past: "The
    end date can't be before today."
  - [edit-absence-overlap] /planning/operations/edit-absence/overlap:
    "This absence overlaps another one."

## Schedule

× - [empty] With no occurrence and no obsolete registration in the shown
×   weeks: "No openings in these weeks."
- [empty] With no occurrence and no obsolete registration in the shown
  weeks: "No openings in these weeks.", above the weeks that hold a
  closed day; the other weeks do not show, and the Today line shows
  only with the current week.
- [closed] A shown day covered by a closure shows "Closed", then the …
  out. …
- [closed-days] Each closed day of the shown weeks, as
  /planning/operations/get-schedule/closed-days, is a shown day, even
  when no occurrence falls on its weekday in the shown weeks.
  date as well. …
  - [opens] The menu opens at once, with its title and a sign that
    the rest is loading, until the load of the click ends.
  - [latest] Once the menu has closed, or a later click has opened it
    again, the load of an earlier click changes nothing on display and
    leads nowhere.
  - [load] Once the load of the last click ends, the menu still open,
    the first that holds:
    1. [load-signed-out] Refused as
       /core/operations/general/signed-out: as /core/ui/access/action.
    2. [menu-past] Its date before today when the load ends: the menu
       shows only its title and "This day is past.", and the Schedule
       shows its weeks again at once, as /planning/ui/schedule/new-day.
    3. [load-failed] Otherwise refused, or failing: the menu shows
       only its title and the generic error, as /ui/errors/generic.
    4. [load-shown] Otherwise: the rest shows.
- [past] In the Occurrence menu, /planning/operations/register/past
  and /planning/operations/change-registration/past: "This day is
  past.", in the menu, or in its confirmation for Cancel registration
  or /planning/ui/occurrence-menu/move;
  the Schedule shows its weeks again at once, as
  /planning/ui/schedule/new-day.
- [taken] In the Occurrence menu, /planning/operations/register/taken:
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

×   - [note] A member whose note holds more than spaces has a note icon,
×     whose text is the note.
  - [note] A member whose note holds more than spaces has a note icon
    named "Note", in French "Note", whose text is the note, given as
    its description.
  - [order] The names are sorted by the member's preference for the …
    registrations, as /planning/model/registration defines the count; …
×     then by
×     display name.
    then by display name, as /ui/name-order.
  any to a manager: "Cancel registration…". …
- [taken-names] An occurrence whose registration is not cancelled, to
  a manager: also the members' display names but that of the
  registration's member, as /planning/ui/occurrence-menu/free shows
  them.
× - [propose] A member's name runs /planning/operations/register for
×   that member, on the occurrence.
- [propose] On a free or cancelled occurrence, a member's name runs
  /planning/operations/register for that member, on the occurrence.
- [move] On an occurrence whose registration is not cancelled, a
  member's name asks "Give this slot to <name> instead of <registered
  name>?" with [Yes, give it] and "Keep it"; "Yes, give it" runs
  /planning/operations/register for that member, on the occurrence,
  replacing its registration.
  - [move-messages] The messages of its tries, "Someone took this slot
    in the meantime." included, show in its confirmation.
  slot in the meantime." …
- [fresh] The message of a refused or failed try shows in the menu
  until the next try or the menu closes: opened again, the menu shows
  no message of an earlier try.

## Shared schedule

  no menu. …
- [new-day] Once today changes while it is open, it shows its weeks
  again as /planning/ui/schedule/new-day, from
  /planning/operations/get-shared-schedule with the token and their
  dates; refused other than as /planning/ui/shared-schedule/gone, or
  failing, it stays as it was, with no message.
- [gone] More weeks, or the refresh of
  /planning/ui/shared-schedule/new-day, refused as
  /planning/operations/get-shared-schedule/unknown: the page shows as
  the link opened then would, as /planning/ui/shared-schedule/invalid.
