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
```

Dialogs:

```
┌ Planning period ───────────────────────────── ✕ ┐
│ From [2026-11-02]   To [2026-11-25]             │
│ [Save]  Cancel                                  │
└─────────────────────────────────────────────────┘

┌ Add a slot ────────────────────────────────── ✕ ┐
│ Day [Thursday ▾]  From [09:00]  To [09:00]      │
│ [Add slot]  Cancel                              │
│ This slot already exists.                       │
└─────────────────────────────────────────────────┘
```

"Edit the slot" has the same fields, filled with the slot, and [Save].
