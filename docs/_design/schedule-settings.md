# Schedule settings

As a manager:

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

Empty, as a manager:

```
PLANNING PERIOD                                               ✎
  None

CLOSURES                                       [+ Add a closure]
  None

SLOTS                                             [+ Add a slot]
  None

SHARE LINK                                  [+ Create a share link]
  None

Members' preferences
  None
```

As a volunteer:

```
(logo)  Jardin partagé des Lilas › Schedule settings       Chloé ▾

PLANNING PERIOD
  Mon 2 Nov 2026 – Wed 25 Nov 2026

CLOSURES
  Sat 14 Nov 2026
  Fête du quartier

SLOTS
  Thursday   10:00–13:00
  Saturday   10:00–13:00
```

After [Copy]:

```
SHARE LINK                                  [+ Create a share link]
  https://gilda.example.org/shared/Hq3v…           [Copy]  🗑
  Link copied.
```

After [Copy], when the browser does not copy the link:

```
SHARE LINK                                  [+ Create a share link]
  https://gilda.example.org/shared/Hq3v…           [Copy]  🗑
  The link couldn't be copied. Select it to copy it.
```

Confirmations:

```
┌───────────────────────────────────────────────────┐
│ Replace the share link? The current link no       │
│ longer shows the Schedule.                        │
│ [Replace]  Cancel                                 │
└───────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────┐
│ Revoke the share link? It no longer shows the     │
│ Schedule.                                         │
│ [Revoke]  Cancel                                  │
└───────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────┐
│ Clear the planning period?                        │
│ [Clear]  Cancel                                   │
└───────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────┐
│ Delete the slot Thursday 10:00–13:00? Its         │
│ registrations from today on become obsolete, and  │
│ the members' preferences on it are deleted.       │
│ [Delete]  Cancel                                  │
└───────────────────────────────────────────────────┘
```

Dialogs:

```
┌ Planning period ───────────────────────────── ✕ ┐
│ From [2026-11-02]   To [2026-11-25]             │
│ [Save]  Cancel                                  │
└─────────────────────────────────────────────────┘

┌ Add a slot ────────────────────────────────── ✕ ┐
│ Day [Thursday ▾]  From [10:00]  To [13:00]      │
│ [Add slot]  Cancel                              │
│ This slot already exists.                       │
└─────────────────────────────────────────────────┘
```

"Edit the slot" has the same fields, filled with the slot, then the
line "Changing the day or times makes its registrations from today on
obsolete.", and [Save].
"Edit the closure" has the fields of "Add a closure", filled with the
closure, then the line "Registrations on its new dates, from today on,
become obsolete; those on the dates it no longer covers may stop being
obsolete.", and [Save].
