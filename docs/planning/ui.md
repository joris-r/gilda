# UI

## Schedule settings

At `/association/<slug>/settings`; mockup in
`design/schedule-settings.md`.

- [french] In French, the screen is "Réglages du planning".

Shows, top to bottom:
- [period] PLANNING PERIOD: its dates, or "None".
- [closures] CLOSURES: each closure's dates and label, by first date,
  or "None".
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
  /planning/operations/set-planning-period.
- [clear-period] The period's delete icon shows only when a period is
  set; it asks "Clear the planning period?" with [Clear], which runs
  /planning/operations/clear-planning-period.
- [add-closure] "Add a closure" opens the dialog "Add a closure": From,
  To, Label, [Add closure]; it runs /planning/operations/add-closure.
- [edit-closure] A closure's edit icon opens the dialog "Edit the
  closure", filled with the closure, with [Save]; it runs
  /planning/operations/edit-closure.
- [delete-closure] A closure's delete icon asks "Delete the closure
  "<label>"?", or "Delete the closure of <first date>?", e.g. "Delete the closure of
  Sat 14 Nov 2026?", without a label,
  with [Delete], which runs /planning/operations/delete-closure.
- [add-slot] "Add a slot" opens the dialog "Add a slot": Day, From,
  To, [Add slot]; it runs /planning/operations/add-slot.
  - [defaults] The dialog opens with From at 09:00 and To at 09:00.
    Changing From sets To to the same time, until the manager changes
    To.
  - [next-slot] After a slot is added, the next Add a slot dialog of
    the screen opens with the added slot's Day, and From and To both
    at its end; To follows From again as in
    /planning/ui/schedule-settings/defaults.
  - [exists] /planning/operations/add-slot/exists: "This slot already
    exists."
- [edit-slot] A slot's edit icon opens the dialog "Edit the slot",
  filled with the slot, with [Save]; From and To do not follow each
  other. It runs /planning/operations/edit-slot.
  - [edit-exists] /planning/operations/edit-slot/exists: "This slot
    already exists."
- [delete-slot] A slot's delete icon asks "Delete the slot <weekday>
  <start>–<end>?" with [Delete], which runs
  /planning/operations/delete-slot.
- [create-link] "Create a share link" runs
  /planning/operations/create-share-link; when there is a link, it
  first asks "Replace the share link? The current link no longer shows
  the Schedule." with [Replace].
- [copy] "Copy" copies the link and shows "Link copied."
- [revoke-link] The link's delete icon asks "Revoke the share link? It
  no longer shows the Schedule." with [Revoke], which runs
  /planning/operations/revoke-share-link.
- [set-preference] A cell of "Members' preferences" saves at once, as
  /planning/ui/my-availability/set.

## My availability

At `/association/<slug>/availability`; mockup in
`design/my-availability.md`.

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
  /planning/operations/set-preference; "—" runs
  /planning/operations/delete-preference.
- [add-absence] "Add an absence" opens the dialog "Add an absence":
  From, To, [Add absence]; it runs /planning/operations/add-absence.
- [edit-absence] An absence's edit icon opens the dialog "Edit the
  absence", filled with it, with [Save]; it runs
  /planning/operations/edit-absence.
- [delete-absence] An absence's delete icon asks "Delete the absence
  of <first> – <last>?", e.g. "Delete the absence of Mon 9 Nov 2026 –
  Sun 15 Nov 2026?", with [Delete], which runs
  /planning/operations/delete-absence.
- [edit-note] The note's edit icon opens the dialog "Note for the
  managers": a multi-line Text, [Save]; it runs
  /planning/operations/set-note.

## Schedule

At `/association/<slug>`; mockups in `design/schedule.md`.

Shows:
- [links] "My availability", "Members" and "Schedule settings",
  leading to those screens.
- [weeks] The weeks of /planning/operations/get-schedule/default, each
  titled "Week <number>", then "More weeks".
- [empty] With no occurrence and no obsolete registration in the shown
  weeks: "No openings in these weeks."
- [today] A line "Today · <date>" separates the past weeks from the
  current week.
- [period-lines] When a planning period is set, a line "Planning start
  · <date>" sits just before the week that holds its first date, and a
  line "Planning end · <date>" just after the week that holds its last
  date. When the first line and the today line fall at the same place,
  the today line comes first.
- [occurrence] An occurrence shows the display name of its
  registration, as /planning/operations/get-schedule/registration, and
  no times:
  - proposed: followed by "?";
  - cancelled: its name struck;
  - no registration: empty.
- [obsolete] An obsolete registration is placed like an occurrence,
  by its date, start and end, marked "obsolete".
- [closed] A day covered by a closure shows "Closed" and the closure's
  label.

Actions:
- [more] "More weeks" adds the four weeks that follow.
- [menu] Clicking an occurrence or an obsolete registration, from
  today on, opens the Occurrence menu on it; after the period's last
  date as well.

## Occurrence menu

Opened on an occurrence or an obsolete registration of Schedule.

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
  - [note] A member whose note holds more than spaces has a note icon,
    whose text is the note.
  - [order] The names are sorted by the member's preference for the
    occurrence's slot: Preferred, Possible, none stated, Unavailable,
    then absent members whatever their preference; then by fewest
    registrations, as /planning/model/registration/count; then by
    display name.
- [confirm] A proposed registration that is not obsolete, the user's
  own, or any to a manager: "Confirm".
- [cancel] A registration that is not cancelled, the user's own, or
  any to a manager: "Cancel registration…".

Actions:
- [sign-up] "Sign up" runs /planning/operations/register for the user.
- [propose] A member's name runs /planning/operations/register for
  that member.
- [taken] /planning/operations/register/taken: "Someone took this
  slot in the meantime."
- [closes] On success, the menu closes and the occurrence shows the
  result.
- [icon] Hovering an icon shows its text; clicking it shows its text
  under the names, in place of the text shown, or hides it when it is
  already shown, and proposes nothing.
- [icon-reset] The text shown leaves when the menu opens on another
  occurrence.
- [escape] Escape closes the menu.
- [confirm-registration] "Confirm" runs
  /planning/operations/change-registration, confirming.
- [cancel-registration] "Cancel registration…" asks "Cancel this
  registration?" with [Yes, cancel] and "Keep it"; "Yes, cancel" runs
  /planning/operations/change-registration, cancelling.

## Shared schedule

At `/shared/<token>`, signed in or not; mockup in
`design/shared-schedule.md`.

- [shown] It shows the association's Schedule as a member sees it,
  from /planning/operations/get-shared-schedule, without the links to
  the other screens; clicking an occurrence opens no menu.
- [invalid] An unknown, replaced or revoked link: "This link is no
  longer valid."
