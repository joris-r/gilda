## `/association/{slug}/settings`: Schedule settings

```
(logo)  Jardin partagé des Lilas › Schedule settings       Alice ▾

PLANNING PERIOD
  Mon 2 Nov 2026 – Wed 25 Nov 2026                      ✎  🗑

CLOSURES                                       [+ Add a closure]
  Sat 14 Nov 2026                                       ✎  🗑
  Fête du quartier
  Thu 24 Dec 2026 – Fri 1 Jan 2027                      ✎  🗑
  Fêtes de fin d'année

SLOTS                                             [+ Add a slot]
  Thursday   10:00–13:00                                ✎  🗑
  Saturday   10:00–13:00                                ✎  🗑

SHARE LINK                                  [+ Create a share link]
  https://gilda.example.org/shared/Hq3v…           [Copy]  🗑

Members' preferences
           Thu 10:00–13:00   Sat 10:00–13:00
  Alice    [Preferred ▾]     [—         ▾]
  Bruno    [Possible  ▾]     [Unavailable ▾]
  Chloé    [—         ▾]     [Preferred ▾]
```

- In French, the screen is "Réglages du planning".
- A volunteer sees the lists and the period, or "None", without the
  add buttons and the edit and delete icons.
- The period's edit icon opens the dialog "Planning period": From, To,
  [Save]. Its delete icon shows only when a period is set; it asks
  "Clear the planning period?" with [Clear].
- "Add a closure" opens the dialog "Add a closure": From, To, Label,
  [Add closure]. A closure's edit icon opens the dialog "Edit the
  closure", filled with the closure, with [Save]. Its delete icon asks
  "Delete the closure "Fête du quartier"?", or "Delete the closure of
  Sat 14 Nov 2026?" without a label, with [Delete].
- Closures are listed by first date.
- "Add a slot" opens the dialog "Add a slot": Day, From, To, [Add
  slot]. A slot's edit icon opens the dialog "Edit the slot", filled
  with the slot, with [Save]; From and To do not follow each other as
  in R17. Its delete icon asks "Delete the slot Thursday 10:00–13:00?"
  with [Delete].
- Slots are listed by weekday, then start.
- Adding a slot the association already has, or saving a slot as
  another one it has, shows "This slot already exists."
- R17: The Add a slot dialog opens with From at 09:00 and To at 09:00.
  Changing From sets To to the same time, until the manager changes To.
- R18: After a slot is added, the next Add a slot dialog of the screen
  opens with the added slot's Day, and From and To both at its end; To
  follows From again as in R17.
- "Share link" is shown to managers only. It shows the link, or
  "None". "Create a share link" creates it, or, when there is one,
  first asks "Replace the share link? The current link no longer
  shows the Schedule." with [Replace]. "Copy" copies the link and
  shows "Link copied.". Its delete icon asks "Revoke the share link?
  It no longer shows the Schedule." with [Revoke]. In French: "Lien de
  partage".
- "Members' preferences" is shown to managers only: one row per member,
  one column per slot, each cell a selector that saves at once like
  those of My availability.
- When "Members' preferences" scrolls horizontally, the member names
  stay in view (not testable).
- In French: "Préférences des membres".

## `/association/{slug}/availability`: My availability

```
(logo)  Jardin partagé des Lilas › My availability        Alice ▾

MY PREFERENCES
  Thursday   10:00–13:00   [Preferred ▾]
  Saturday   10:00–13:00   [—         ▾]

ABSENCES                                     [+ Add an absence]
  Mon 9 Nov 2026 – Sun 15 Nov 2026                      ✎  🗑

NOTE FOR THE MANAGERS                                         ✎
  Always group my registrations in pairs.
```

- Every member, manager or volunteer, sees and changes only their own
  preferences, absences and note here.
- A selector on each slot sets the member's preference; choosing a
  value saves it at once; "—" deletes it.
- Slots are listed by weekday, then start.
- Each value has a colour: Preferred green, Possible orange,
  Unavailable red; "—" has none. Selectors show their value's colour,
  here and in Members' preferences. (Look of colours not testable.)
- With no slot, no absence or an empty note, the section shows "None".
- Absences are listed from those ending today on; earlier ones do not
  show.
- "Add an absence" opens the dialog "Add an absence": From, To, [Add
  absence]. An absence's edit icon opens the dialog "Edit the
  absence", filled with it, with [Save]. Its delete icon asks "Delete
  the absence of Mon 9 Nov 2026 – Sun 15 Nov 2026?" with [Delete].
- The note's edit icon opens the dialog "Note for the managers": a
  multi-line Text, [Save].
- In French: "Mes disponibilités", "Mes préférences", "Préféré",
  "Possible", "Indisponible", "Absences", "Ajouter une absence",
  "Note pour les responsables".

## `/association/{slug}`: Schedule

Wide screen:

```
(logo)  Jardin partagé des Lilas                           Alice ▾
                      My availability  Members  Schedule settings

Week 43
       Thu 22 Oct        Sat 24 Oct
10h  ┌──────────────┐  ┌──────────────┐
     │Alice         │  │              │
13h  └──────────────┘  └──────────────┘

── Today · Wednesday 28 October 2026 ───────────────────────

Week 44
       Thu 29 Oct        Sat 31 Oct
10h  ┌──────────────┐  ┌──────────────┐
     │Chloé         │  │Bruno ?       │
13h  └──────────────┘  └──────────────┘

── Planning start · Monday 2 November 2026 ─────────────────

Week 45
       Thu 5 Nov         Sat 7 Nov
10h  ┌──────────────┐  ┌──────────────┐
     │~~Alice~~     │  │   Closed     │
13h  └──────────────┘  │Fête du quart.│
                        └──────────────┘
…
Week 48
       Thu 26 Nov        Sat 28 Nov
       (greyed)          (greyed)

── Planning end · Wednesday 25 November 2026 ───────────────

Week 49      (greyed)
…
[More weeks]
```

Narrow screen, same weeks:

```
Week 44
         10h        13h
Thu 29   [Chloé      ]
Sat 31   [Bruno ?    ]
```

- "My availability", "Members" and "Schedule settings" lead to those
  screens.
- It opens on the weeks of R32; "More weeks", at the end, adds four
  more.
- Each week has one column per weekday on which an occurrence of the
  shown weeks falls. Time runs down, on the same scale in every week,
  from the earliest start to the latest end of the shown occurrences,
  rounded to whole hours: an occurrence is placed and sized by its
  start and end. Occurrences of a day that overlap sit side by side.
  (Placement and sizes not testable.)
- On a narrow screen, each week has one row per such weekday, and time
  runs from left to right. (Not testable.)
- A line marked with today's date separates the past weeks from the
  current week; the days before today look different from the others
  (look of past days not testable).
- When a planning period is set, a line marked with its first date sits
  just before the week that holds it; a line marked with its last
  date, just after the week that holds it. When the first line and the
  today line fall at the same place, the today line comes first. The
  two lines and the background of the days within the period share an
  accent colour, used by nothing else on the screen. (Look not
  testable.)
- Occurrences and obsolete registrations after the period's last date
  are greyed, and keep their menu. (Look not testable.)
- An occurrence shows its registration's display name, and no times:
  green when confirmed; orange with "?" when proposed; red when it has
  no registration (empty) or a cancelled one, whose name is struck.
  (Colours not testable.)
- An obsolete registration is placed like an occurrence, by its date,
  start and end, marked "obsolete".
- A day covered by a closure shows "Closed" and the closure's label.
- Clicking an occurrence or an obsolete registration, from today on,
  opens a menu on it, titled with its day and times, e.g. "Thu 29 Oct
  · 10–13":
  - free or cancelled: "Sign up"; for a manager, also the members'
    display names, each proposing the occurrence to that member. Each
    name is followed by the member's registration count in
    parentheses, e.g. "Alice (2)"; without a planning period, no count
    is shown. A member is absent when one of their absences covers the
    occurrence's date. Each name has the background colour of the
    member's preference for the occurrence's slot, none when they have
    stated none, or grey when they are absent (look of colours not
    testable). An absent member's name has an absence icon, whose text
    is "Absent Mon 9 Nov 2026 – Sun 15 Nov 2026", the absence covering
    the occurrence's date; a member with a non-empty note has a note
    icon, whose text is the note. Hovering an icon shows its text;
    clicking it shows its text under the names, in place of the text
    shown, or hides it when it is already shown, and proposes nothing.
    In French: "Absent du lun. 9 nov. 2026 au dim. 15 nov. 2026";
  - R27: The names are sorted by the member's preference for the
    occurrence's slot: Preferred, Possible, none stated, Unavailable,
    then absent members whatever their preference; then by fewest
    registrations (R15); then by display name;
  - the user's own proposed registration, or any proposed one for a
    manager: "Confirm";
  - the user's own registration, or any for a manager: "Cancel
    registration…", which asks "Cancel this registration? [Yes,
    cancel] Keep it" before cancelling.

## `/shared/{token}`: Shared schedule

```
(logo)  Jardin partagé des Lilas                       [English ▾]

Week 44
       Thu 29 Oct        Sat 31 Oct
10h  ┌──────────────┐  ┌──────────────┐
     │Chloé         │  │Bruno ?       │
13h  └──────────────┘  └──────────────┘
…
[More weeks]
```

- Reached from a share link, signed in or not.
- It shows the association's Schedule as a member sees it, without
  the links to the other screens; clicking an occurrence opens no
  menu.
- An unknown, replaced or revoked link shows "This link is no longer
  valid."
