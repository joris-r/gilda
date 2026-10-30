# Interface

- The interface opens in French when the browser prefers French, in
  English otherwise.

## Header

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
- Signed in, the header's location stands for the screen's title;
  screens have no back link.

## Look

- The interface follows the browser's light or dark preference (not
  testable).
- The accent colour is orange (not testable).
