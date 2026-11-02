# Interface

- The interface opens in French when the browser prefers French, in
  English otherwise.
- An email the user triggers (e.g. the confirmation email) is in the
  interface's language.

## Header

Signed in:

```
(logo)  Jardin partagé des Lilas › Members                 Alice ▾
                                           ┌────────────────────────┐
                                           │ [English ▾]            │
                                           │ Revoke my sign-in link │
                                           │ Sign out               │
                                           └────────────────────────┘
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
  - Members, Schedule settings, My availability: the association's
    name, then the screen's name;
  - New association: "My associations", leading to `/`, then "New
    association".
- The association's name leads to its Schedule.
- A long location is shortened on a narrow screen (not testable).
- Signed in, the user's display name opens a menu with the language
  selector, "Revoke my sign-in link" and Sign out. Signed out, the
  language selector stands alone at the header's right.
- "Revoke my sign-in link" asks "Revoke your sign-in link? Sessions
  opened with it are signed out. [Confirm] Cancel"; Confirm revokes it
  and shows "Your sign-in link is revoked.", or leads to Sign in when
  this session was opened with it.
- The language selector switches between English and French; the
  choice is kept in the browser across visits and wins over the
  browser's preference.
- Signed in, the header's location stands for the screen's title;
  screens have no back link.

## Forms

```
                                              [+ Add a closure]
  Sat 14 Nov 2026                                          🗑
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

## Look

- The interface follows the browser's light or dark preference (not
  testable).
- The accent colour is orange (not testable).
