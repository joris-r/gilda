# forms: create from a button, edit from an icon

On My associations, Members and Schedule settings, every creation opens
a form from a button and every edit opens one from an icon; no form
stays open on these screens.

## Interface

New section, after Header:

### Forms

```
                                              [+ Add a closure]
  Sat 14 Nov 2026                                       ✎  🗑
  Fête du quartier

┌ Add a closure ──────────────────────────────── ✕ ┐
│ From [          ]   To [          ]              │
│ Label [                            ]             │
│ [Add closure]  Cancel                            │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ Delete the closure "Fête du quartier"?           │
│ [Delete]  Cancel                                 │
└──────────────────────────────────────────────────┘
```

- A button, "+" then its name, opens a form to create; an edit icon on
  a line opens a form to change it; a delete icon on a line asks for
  confirmation. Each icon is named by its action, e.g. "Edit the
  period", "Delete the closure".
- A form opens in a dialog with a title, its fields, its submit button,
  Cancel and a close button. Cancel, the close button and Escape close
  it, changing nothing.
- On success, the dialog closes and the screen shows the result and its
  message, if any. On failure, the dialog stays open, with its message.
- A confirmation opens in a dialog with its question, its action button
  and Cancel. Confirming one asked from a form's dialog also closes that
  form.
- On a narrow screen, a dialog spans the screen's width at its bottom
  (not testable).
- Only managers see the buttons and icons that create, edit or delete.

Header, modified: the location of New association is "My associations",
leading to `/`, then "New association".

## Screens

### `/`, signed in: My associations

Modified mock-up, replacing "+" and its form:

```
(logo)  My associations                                    Alice ▾

  Jardin partagé des Lilas                 MANAGER
    …
  Atelier vélo                           VOLUNTEER
    No upcoming registration.

[+ New association]
```

- "New association", below the list, leads to `/associations/new`.

Removed: "+", named "Create an association", and the form it shows.

### `/associations/new`: New association

New screen:

```
(logo)  My associations › New association                  Alice ▾

New association
  Name  [                    ]
  [Create association]  Cancel
```

- Creating leads to the new association's Schedule; Cancel leads to My
  associations.

### `/associations/{id}/members`: Members

Modified mock-up, as a manager:

```
(logo)  Jardin partagé des Lilas › Members                 Alice ▾

                                                  [+ Add a member]
  Alice                                        MANAGER   ✎
  alice@example.org
  Chloé  not joined yet                      VOLUNTEER   ✎
  chloe@example.org
  …
  Show all 7 members
```

- "Add a member" opens the dialog "Add a member": Display name, Email,
  Role (Volunteer by default), [Add member].
- The edit icon on Chloé, named "Edit Chloé", opens the dialog:

```
┌ Chloé ───────────────────────────────────────── ✕ ┐
│ chloe@example.org                                 │
│ Role [Volunteer ▾]                                │
│ [Save]  Cancel                                    │
│                                                   │
│ SIGN-IN LINK                                      │
│ [Send link]  Revoke link                          │
└───────────────────────────────────────────────────┘
```

- Save with another role changes it and shows "Chloé is now manager.";
  with the same role, it closes the dialog and changes nothing.
- "Revoke link" shows only for a member with an access link; it asks
  "Revoke Chloé's sign-in link?" with [Revoke]; confirming revokes it
  and shows "Chloé's sign-in link is revoked."
- "Send link" asks "Send Chloé's sign-in link by email?" with [Send];
  confirming sends it (R26) and shows "Chloé's sign-in link is sent."
- A volunteer sees the members and their roles, without "Add a member"
  and without the edit icons.

Replaces: the "Members" mock-up, the "Add a member" form and its
placement below the list, "Change role" and its "Make Bruno manager?
[Confirm] Cancel", the "Revoke link" and "Send link" actions on each
line, and the rule on what a volunteer sees. The messages "Chloé
added.", "Chloé is already a member.", "An association keeps at least
one manager." and "We couldn't send Chloé's sign-in link. Try again
later." are unchanged, shown as the Forms section says.

### `/associations/{id}/settings`: Schedule settings

Modified mock-up, as a manager:

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

MEMBERS' PREFERENCES
  …
```

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
- R17 applies to the Add a slot dialog.
- R18, modified: After a slot is added, the next Add a slot dialog of
  the screen opens with the added slot's Day, and From and To both at
  its end; To follows From again as in R17.
- A volunteer sees the lists and the period, or "None", without the
  add buttons and the edit and delete icons.

Replaces: the mock-up, the period's From, To, [Save] and [Clear] on the
screen, the closure and slot forms below their lists, each line's
"Delete", R18, and the rule on what a volunteer sees.
