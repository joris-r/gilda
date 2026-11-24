# UI

## Schedule settings

At `/association/<slug>/settings`; mockup in
`_design/schedule-settings.md`.

- [french] In French, the screen is "Réglages du planning".

Shows, top to bottom:
- [period] PLANNING PERIOD: its dates, or "None".
- [closures] CLOSURES: the closures ending today or later, each with
  its dates and label, by first date, or "None"; earlier ones do not
  show.
- [slots] SLOTS: each slot's weekday and times, by weekday, then
  start, or "None".
- [share-link] To managers only, SHARE LINK: the link, or "None". In
  French: "Lien de partage".
- [preferences] To managers only, "Members' preferences": one row per
  member, one column per slot, each cell a selector of the member's
  preference on the slot. In French: "Préférences des membres".
  - [preferences-none] Without a slot: "None".
  - [preferences-order] Its rows follow the order of
    /core/ui/members/list, its columns that of
    /planning/ui/schedule-settings/slots.
- [volunteer] A volunteer sees the lists and the period, without the
  add buttons and the edit and delete icons.

Actions:
- [edit-period] The period's edit icon opens the dialog "Planning
  period": From, To, [Save]; it runs
  /planning/operations/set-planning-period with the fields.
  - [period-order] /planning/operations/set-planning-period/order: "The
    end date can't be before the start date."
- [clear-period] The period's delete icon shows only when a period is
  set; it asks "Clear the planning period?" with [Clear], which runs
  /planning/operations/clear-planning-period.
- [add-closure] "Add a closure" opens the dialog "Add a closure": From,
  To, Label, [Add closure]; it runs /planning/operations/add-closure
  with the fields.
  - [closure-order] /planning/operations/add-closure/order: "The end
    date can't be before the start date."
  - [closure-past] /planning/operations/add-closure/past: "The end date
    can't be before today."
  - [closure-warning] The dialog shows "Registrations on its dates,
    from today on, become obsolete."
- [edit-closure] A closure's edit icon opens the dialog "Edit the
  closure", filled with the closure, with [Save]; it runs
  /planning/operations/edit-closure for it, with the fields.
  - [edit-closure-order] /planning/operations/edit-closure/order: "The
    end date can't be before the start date."
  - [edit-closure-past] /planning/operations/edit-closure/past: "The
    end date can't be before today."
  - [edit-closure-warning] The dialog shows "Registrations on its new
    dates, from today on, become obsolete; those on the dates it no
    longer covers may stop being obsolete."
- [delete-closure] A closure's delete icon asks "Delete the closure
  "<label>"?", or, without a label, "Delete the closure of <first
  date>?", e.g. "Delete the closure of Sat 14 Nov 2026?", with
  [Delete], which runs /planning/operations/delete-closure for
  it.
  - [delete-closure-warning] The question goes on with "Registrations
    on its dates, from today on, may stop being obsolete."
- [add-slot] "Add a slot" opens the dialog "Add a slot": Day, From,
  To, [Add slot]; it runs /planning/operations/add-slot with the
  fields.
  - [defaults] The dialog opens with From at 09:00 and To at 09:00.
    Changing From sets To to the same time, until the manager changes
    To.
  - [next-slot] After a slot is added, the next Add a slot dialog of
    the screen opens with the added slot's Day, and From and To both
    at its end; To follows From again as in
    /planning/ui/schedule-settings/defaults.
  - [exists] /planning/operations/add-slot/exists: "This slot already
    exists."
  - [order] /planning/operations/add-slot/order: "The end time must be
    after the start time."
- [edit-slot] A slot's edit icon opens the dialog "Edit the slot",
  filled with the slot, with [Save]; From and To do not follow each
  other. It runs /planning/operations/edit-slot for it, with the
  fields.
  - [edit-exists] /planning/operations/edit-slot/exists: "This slot
    already exists."
  - [edit-order] /planning/operations/edit-slot/order: "The end time
    must be after the start time."
  - [edit-warning] The dialog shows "Changing the day or times makes
    its registrations from today on obsolete."
- [delete-slot] A slot's delete icon asks "Delete the slot <weekday>
  <start>–<end>?" with [Delete], which runs
  /planning/operations/delete-slot for it.
  - [delete-slot-warning] The question goes on with "Its registrations
    from today on become obsolete, and the members' preferences on it
    are deleted."
- [create-link] "Create a share link" runs
  /planning/operations/create-share-link; when there is a link, it
  first asks "Replace the share link? The current link no longer shows
  the Schedule." with [Replace].
- [copy] "Copy" copies the link and shows "Link copied.", in place of
  the message of an earlier Copy.
  - [copy-failed] When the browser does not copy it: "The link
    couldn't be copied. Select it to copy it." instead.
- [revoke-link] The link's delete icon asks "Revoke the share link? It
  no longer shows the Schedule." with [Revoke], which runs
  /planning/operations/revoke-share-link.
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

At `/association/<slug>/availability`; mockup in
`_design/my-availability.md`.

- [own] Every member, manager or volunteer, sees and changes only
  their own preferences, absences and note here.

Shows, top to bottom:
- [preferences] MY PREFERENCES: each slot's weekday and times, by
  weekday, then start, with a
  selector of the member's preference on it: Preferred, Possible,
  Unavailable, or "—" for none.
- [absences] ABSENCES: the absences ending today or later, by first
  date; earlier ones do not show.
- [note] NOTE FOR THE MANAGERS: the note.
- [none] With no slot, no absence shown or an empty note, the section
  shows "None".
- [french] In French: "Mes disponibilités", "Mes préférences",
  "Préféré", "Possible", "Indisponible", "Absences", "Ajouter une
  absence", "Note pour les responsables".

Actions:
- [set] Choosing a value saves it at once, running
  /planning/operations/set-preference with the user as member, the
  slot and the value; "—" runs /planning/operations/delete-preference
  with the user as member and the slot.
  - [saved-value] While a save of the selector runs, it shows the last
    value chosen. Once none runs, it shows the value of the save that
    succeeded last, in the order the answers came, or else the value
    it opened with: a refused or failed save does not change it.
- [add-absence] "Add an absence" opens the dialog "Add an absence":
  From, To, [Add absence]; it runs /planning/operations/add-absence
  with the fields.
  - [absence-order] /planning/operations/add-absence/order: "The end
    date can't be before the start date."
  - [absence-past] /planning/operations/add-absence/past: "The end date
    can't be before today."
  - [absence-overlap] /planning/operations/add-absence/overlap: "This
    absence overlaps another one."
- [edit-absence] An absence's edit icon opens the dialog "Edit the
  absence", filled with it, with [Save]; it runs
  /planning/operations/edit-absence for it, with the fields.
  - [edit-absence-order] /planning/operations/edit-absence/order: "The
    end date can't be before the start date."
  - [edit-absence-past] /planning/operations/edit-absence/past: "The
    end date can't be before today."
  - [edit-absence-overlap] /planning/operations/edit-absence/overlap:
    "This absence overlaps another one."
- [delete-absence] An absence's delete icon asks "Delete the absence
  of <first> – <last>?", e.g. "Delete the absence of Mon 9 Nov 2026 –
  Sun 15 Nov 2026?", with [Delete], which runs
  /planning/operations/delete-absence for it.
- [edit-note] The note's edit icon opens the dialog "Note for the
  managers": a multi-line Text, [Save]; it runs
  /planning/operations/set-note with the field.

## Schedule

At `/association/<slug>`; mockups in `_design/schedule.md`.

Shows:
- [links] "My availability", "Members" and "Schedule settings",
  leading to those screens.
- [weeks] The weeks of /planning/operations/get-schedule/default, each
  titled "Week <number>", then "More weeks".
- [empty] With no occurrence and no obsolete registration in the shown
  weeks: "No openings in these weeks.", above the weeks that hold a
  closed day; the other weeks do not show, and the Today line shows
  only with the current week.
- [today] A line "Today · <date>" separates the past weeks from the
  current week.
- [period-lines] When a planning period is set, a line "Planning start
  · <date>" sits just before the week that holds its first date, and a
  line "Planning end · <date>" just after the week that holds its last
  date. A line whose week is not shown is not shown. Lines at the same
  place come in this order: Planning end, Today, Planning start.
- [occurrence] An occurrence shows the display name of its
  registration, as /planning/operations/get-schedule/registration, and
  no times:
  - proposed: followed by "?";
  - cancelled: its name struck;
  - no registration: empty.
- [obsolete] An obsolete registration is placed like an occurrence,
  by its date, start and end, marked "obsolete".
- [closed] A shown day covered by a closure shows "Closed", then the
  labels of the closures covering it, by first date (free among the
  same first date), separated by " · ", each once and empty ones left
  out.
- [closed-days] Each closed day of the shown weeks, as
  /planning/operations/get-schedule/closed-days, is a shown day, even
  when no occurrence falls on its weekday in the shown weeks.

Actions:
- [more] "More weeks" adds the four weeks that follow, from
  /planning/operations/get-schedule with their dates.
- [menu] Clicking an occurrence or an obsolete registration, from
  today on, opens the Occurrence menu on it; after the period's last
  date as well.
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
  past.", in the menu, or in its confirmation for Cancel registration,
  /planning/ui/occurrence-menu/move or
  /planning/ui/occurrence-menu/take-over-ask;
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

Opened on an occurrence or an obsolete registration of Schedule;
mockup in `_design/occurrence-menu.md`.

Shows:
- [title] Its day and times, e.g. "Thu 29 Oct · 10–13".
- [free] Free or cancelled: "Sign up"; to a manager, also the
  members' display names.
  - [count] Each name is followed by the member's registration count
    in parentheses, e.g. "Alice (2)"; without a planning period, no
    count.
  - [absent] A member is absent when one of their absences covers the
    occurrence's date. An absent member's name has an absence icon,
    whose text is "Absent <first> – <last>", the absence covering the
    date, e.g. "Absent Mon 9 Nov 2026 – Sun 15 Nov 2026"; in French,
    "Absent du lun. 9 nov. 2026 au dim. 15 nov. 2026".
  - [absent-day] For an absence of a single day: "Absent <date>".
  - [note] A member whose note holds more than spaces has a note icon
    named "Note", in French "Note", whose text is the note, given as
    its description.
  - [order] The names are sorted by the member's preference for the
    occurrence's slot: Preferred, Possible, none stated, Unavailable,
    then absent members whatever their preference; then by fewest
    registrations, as /planning/model/registration defines the count;
    then by display name, as /ui/name-order.
- [confirm] A proposed registration that is not obsolete, the user's
  own, or any to a manager: "Confirm".
- [cancel] A registration that is not cancelled, the user's own, or
  any to a manager: "Cancel registration…".
- [taken-names] An occurrence whose registration is not cancelled, to
  a manager: also the members' display names but that of the
  registration's member, as /planning/ui/occurrence-menu/free shows
  them.
- [take-over] An occurrence whose registration is not cancelled and
  is another member's, to a volunteer: "Take over this slot…".

Actions:
- [sign-up] "Sign up" runs /planning/operations/register with the user
  as member, on the occurrence.
- [propose] On a free or cancelled occurrence, a member's name runs
  /planning/operations/register for that member, on the occurrence.
- [move] On an occurrence whose registration is not cancelled, a
  member's name asks "Give this slot to <name> instead of <registered
  name>?" with [Yes, give it] and "Keep it"; "Yes, give it" runs
  /planning/operations/register for that member, on the occurrence,
  replacing its registration.
  - [move-messages] The messages of its tries, "Someone took this slot
    in the meantime." included, show in its confirmation.
- [take-over-ask] "Take over this slot…" asks "Take this slot from
  <registered name>?" with [Yes, take it] and "Keep it"; "Yes, take
  it" runs /planning/operations/register with the user as member, on
  the occurrence, replacing its registration.
  - [take-over-messages] The messages of its tries, "Someone took this
    slot in the meantime." included, show in its confirmation.
- [taken] /planning/operations/register/taken: "Someone took this
  slot in the meantime."
- [fresh] The message of a refused or failed try shows in the menu
  until the next try or the menu closes: opened again, the menu shows
  no message of an earlier try.
- [closes] On success, the menu closes and the occurrence shows the
  result.
- [icon] Hovering an icon shows its text; clicking it shows its text
  under the names, in place of the text shown, or hides it when it is
  already shown, and proposes nothing.
- [icon-reset] The text shown leaves when the menu opens on another
  occurrence.
- [escape] Escape closes the menu.
- [confirm-registration] "Confirm" runs
  /planning/operations/change-registration on the registration,
  confirming.
- [cancel-registration] "Cancel registration…" asks "Cancel this
  registration?" with [Yes, cancel] and "Keep it"; "Yes, cancel" runs
  /planning/operations/change-registration on the registration,
  cancelling.

## Shared schedule

At `/shared/<token>`, signed in or not; mockup in
`_design/shared-schedule.md`.

- [shown] It shows the association's Schedule as a member sees it,
  from /planning/operations/get-shared-schedule with the token,
  without the links to the other screens; clicking an occurrence opens
  no menu.
- [new-day] Once today changes while it is open, it shows its weeks
  again as /planning/ui/schedule/new-day, from
  /planning/operations/get-shared-schedule with the token and their
  dates; refused other than as /planning/ui/shared-schedule/gone, or
  failing, it stays as it was, with no message.
- [invalid] An unknown, replaced or revoked link: "This link is no
  longer valid."
- [gone] More weeks, or the refresh of
  /planning/ui/shared-schedule/new-day, refused as
  /planning/operations/get-shared-schedule/unknown: the page shows as
  the link opened then would, as /planning/ui/shared-schedule/invalid.
- [status] It answers 200, the link valid or not.
