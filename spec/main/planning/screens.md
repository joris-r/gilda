# Screens

## `/associations/{id}/opening`: Opening hours

```
← Jardin partagé
Opening hours

Slots
  Thursday   10:00–13:00   Delete
  Saturday   10:00–13:00   Delete
  Day [Thursday ▾]  From [10:00]  To [13:00]  [Add slot]

Closures
  Sat 14 Nov 2026                  Fête du quartier   Delete
  Thu 24 Dec 2026 – Fri 1 Jan 2027  Fêtes de fin d'année   Delete
  From [    ]  To [    ]  Label [          ]  [Add closure]

Planning period
  Mon 2 Nov 2026 – Wed 25 Nov 2026
  From [2026-11-02]  To [2026-11-25]  [Save]  [Clear]
```

- A volunteer sees the lists and the period, or "None", without Delete
  and without the forms.

## `/associations/{id}/schedule`: Schedule

Wide screen:

```
← Jardin partagé
Schedule

Week 43 · 19 – 25 Oct
       Thu 22 Oct        Sat 24 Oct
10h  ┌──────────────┐  ┌──────────────┐
     │10–13 Alice   │  │10–13         │
13h  └──────────────┘  └──────────────┘

── Today · Wednesday 28 October 2026 ───────────────────────

Week 44 · 26 Oct – 1 Nov
       Thu 29 Oct        Sat 31 Oct
10h  ┌──────────────┐  ┌──────────────┐
     │10–13 Chloé   │  │10–13 Bruno ? │
13h  └──────────────┘  └──────────────┘

── Planning period · from Monday 2 November 2026 ───────────

Week 45 · 2 – 8 Nov
       Thu 5 Nov         Sat 7 Nov
10h  ┌──────────────┐  ┌──────────────┐
     │10–13 ~~Alice~~│  │   Closed     │
13h  └──────────────┘  │Fête du quart.│
                        └──────────────┘
…
Week 48 · 23 – 29 Nov
       Thu 26 Nov        Sat 28 Nov
       (greyed)          (greyed)

── End of planning period · Wednesday 25 November 2026 ─────

Week 49 · 30 Nov – 6 Dec      (greyed)
…
[More weeks]
```

Narrow screen, same weeks:

```
Week 44 · 26 Oct – 1 Nov
         10h        13h
Thu 29   [Chloé      ]
Sat 31   [Bruno ?    ]
```

- It opens on the week before the current one and shows six weeks;
  "More weeks", at the end, adds four more.
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
    display names, each proposing the occurrence to that member;
  - the user's own proposed registration, or any proposed one for a
    manager: "Confirm";
  - the user's own registration, or any for a manager: "Cancel
    registration…", which asks "Cancel this registration? [Yes,
    cancel] Keep it" before cancelling.
