## `/associations/{id}/settings`: Schedule settings

```
(logo)  Jardin partagé des Lilas › Schedule settings       Alice ▾

PLANNING PERIOD
  Mon 2 Nov 2026 – Wed 25 Nov 2026                      ✎  🗑

CLOSURES                                       [+ Add a closure]
  Sat 14 Nov 2026                                          🗑
  Fête du quartier
  Thu 24 Dec 2026 – Fri 1 Jan 2027                         🗑
  Fêtes de fin d'année

SLOTS                                             [+ Add a slot]
  Thursday   10:00–13:00   My preference [Preferred ▾]     🗑
  Saturday   10:00–13:00   My preference [—         ▾]     🗑

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
  [Add closure]. A closure's delete icon asks "Delete the closure
  "Fête du quartier"?", or "Delete the closure of Sat 14 Nov 2026?"
  without a label, with [Delete].
- "Add a slot" opens the dialog "Add a slot": Day, From, To, [Add
  slot]. A slot's delete icon asks "Delete the slot Thursday
  10:00–13:00?" with [Delete].
- R17: The Add a slot dialog opens with From at 09:00 and To at 09:00.
  Changing From sets To to the same time, until the manager changes To.
- R18: After a slot is added, the next Add a slot dialog of the screen
  opens with the added slot's Day, and From and To both at its end; To
  follows From again as in R17.
- Every member sees "My preference" on each slot. Choosing a value
  saves it at once; "—" deletes it.
- "Members' preferences" is shown to managers only: one row per member,
  one column per slot, each cell a selector that saves at once like
  "My preference".
- When "Members' preferences" scrolls horizontally, the member names
  stay in view (not testable).
- Each value has a colour: Preferred green, Possible orange,
  Unavailable red; "—" has none. Selectors show their value's colour.
  (Look of colours not testable.)
- In French: "Mes préférences", "Préférences des membres", "Préféré",
  "Possible", "Indisponible".

## `/associations/{id}`: Schedule

Wide screen:

```
(logo)  Jardin partagé des Lilas                           Alice ▾
                                       Members  Schedule settings

Week 43
       Thu 22 Oct        Sat 24 Oct
10h  ┌──────────────┐  ┌──────────────┐
     │10–13 Alice   │  │10–13         │
13h  └──────────────┘  └──────────────┘

── Today · Wednesday 28 October 2026 ───────────────────────

Week 44
       Thu 29 Oct        Sat 31 Oct
10h  ┌──────────────┐  ┌──────────────┐
     │10–13 Chloé   │  │10–13 Bruno ? │
13h  └──────────────┘  └──────────────┘

── Planning period · from Monday 2 November 2026 ───────────

Week 45
       Thu 5 Nov         Sat 7 Nov
10h  ┌──────────────┐  ┌──────────────┐
     │10–13 ~~Alice~~│  │   Closed     │
13h  └──────────────┘  │Fête du quart.│
                        └──────────────┘
…
Week 48
       Thu 26 Nov        Sat 28 Nov
       (greyed)          (greyed)

── End of planning period · Wednesday 25 November 2026 ─────

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

- "Members" and "Schedule settings" lead to those screens.
- It opens on the week before the current one and shows six weeks,
  and more if needed to reach the week after the one that holds the
  planning period's last date; "More weeks", at the end, adds four
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
  today line fall at the same place, the today line comes first.
- Occurrences and obsolete registrations after the period's last date
  are greyed, and keep their menu. (Look not testable.)
- An occurrence shows its times and its registration's display name:
  green when confirmed; orange with "?" when proposed; red when it has
  no registration (times only) or a cancelled one, whose name is
  struck.
  (Colours not testable.)
- An obsolete registration is placed like an occurrence, by its date,
  start and end, marked "obsolete".
- A day covered by a closure shows "Closed" and the closure's label.
- Clicking an occurrence or an obsolete registration, from today on,
  opens a menu on it:
  - free or cancelled: "Sign up"; for a manager, also the members'
    display names, each proposing the occurrence to that member. Each
    name has the background colour of the member's preference for the
    occurrence's slot, none when they have stated none (look of colours
    not testable), and is followed by the member's registration count
    in parentheses, e.g. "Alice (2)"; without a planning period, no
    count is shown;
  - the user's own proposed registration, or any proposed one for a
    manager: "Confirm";
  - the user's own registration, or any for a manager: "Cancel
    registration…", which asks "Cancel this registration? [Yes,
    cancel] Keep it" before cancelling.
