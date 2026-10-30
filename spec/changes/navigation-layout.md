# Navigation and layout

The Schedule becomes the association's main page, the header shows
where the user is and gathers the user's actions in a menu, and the
rarely used forms and lists take less room.

## Interface

Replaces "The header shows the logo alone, which leads to `/`" and the
language selector rule.

Signed in:

```
(logo)  Jardin partagé des Lilas › Members                 Alice ▾
                                                   ┌────────────────┐
                                                   │ [English ▾]    │
                                                   │ Sign out       │
                                                   └────────────────┘
```

Signed out:

```
(logo)                                                [English ▾]
```

- The logo leads to `/` (not testable).
- To the right of the logo, signed in, the header shows where the user
  is:
  - My associations: "My associations";
  - Schedule: the association's name;
  - Members, Schedule settings: the association's name, then the
    screen's name.
- The association's name leads to its Schedule.
- A long location is shortened on a narrow screen (not testable).
- Signed in, the user's display name opens a menu with the language
  selector and Sign out. Signed out, the language selector stands
  alone at the header's right.
- The language selector switches between English and French; the
  choice is kept in the browser across visits and wins over the
  browser's preference.

## Screens

The header's location replaces each screen's back link and title.

### `/`, signed in: My associations

Replaces the drawing of My associations:

```
(logo)  My associations                                    Alice ▾

                                                              [+]
  Jardin partagé des Lilas                 MANAGER
  Repair Café Belleville                 VOLUNTEER
```

- "+", named "Create an association", shows the form:

```
Create an association
  Name  [                    ]
  [Create association]
```

### `/associations/{id}/members`: Members

Replaces `/associations/{id}`: Association. As a manager:

```
(logo)  Jardin partagé des Lilas › Members                 Alice ▾

  Alice                                  MANAGER  Change role
  alice@example.org
  Bruno                                VOLUNTEER  Change role
  bruno@example.org
  Chloé  no account                    VOLUNTEER  Change role
  chloe@example.org
  David  pending                       VOLUNTEER  Change role
  david@example.org
  Emma                                 VOLUNTEER  Change role
  emma@example.org
  Show all 7 members

[Add a member]
```

- The first 5 members show; "Show all 7 members" shows the others.
  With 5 members or fewer, all show and the link does not.
- "Add a member" shows the Add a member form.
- The other rules of Association are unchanged.

### `/associations/{id}/settings`: Schedule settings

Replaces `/associations/{id}/opening`: Opening hours, with the
sections in a new order:

```
(logo)  Jardin partagé des Lilas › Schedule settings       Alice ▾

Planning period
  …
Closures
  …
Slots
  …
```

- In French, the screen is "Réglages du planning".

### `/associations/{id}`: Schedule

Replaces `/associations/{id}/schedule`: Schedule. Wide screen:

```
(logo)  Jardin partagé des Lilas                           Alice ▾
                                       Members  Schedule settings

Week 43
       Thu 22 Oct        Sat 24 Oct
…
Week 48
…
── End of planning period · Wednesday 25 November 2026 ─────

Week 49      (greyed)

[More weeks]
```

- "Members" and "Schedule settings" lead to those screens.
- Week headings show only the week number, on wide and narrow screens
  ("Week 44" replaces "Week 44 · 26 Oct – 1 Nov").
- Replaces "It opens on the week before the current one and shows six
  weeks": it opens on the week before the current one and shows six
  weeks, and more if needed to reach the week after the one that holds
  the planning period's last date.

## Scenarios

In "A volunteer becomes manager":

- Step 2: "On its Members page, she adds Bruno…" replaces "On its
  Association page".
- Step 4: "opens the Members of Jardin partagé and promotes Chloé"
  replaces "opens Jardin partagé and promotes Chloé".

## Removed

- The URLs `/associations/{id}/schedule` and `/associations/{id}/opening`.
- The "← My associations" and "← Jardin partagé" back links.
