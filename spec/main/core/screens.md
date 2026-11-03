# Screens

## `/`, signed out: Sign in

```
(logo)                                     [English ▾]

Sign in
  Email     [                    ]
  Password  [                    ]
  [Sign in]
  Forgot your password?
  Sign in with an email link

No account yet? Create an account
```

- Wrong credentials show "Wrong email or password." under the form.
- "Create an account" leads to `/signup`.
- "Forgot your password?" leads to `/forgot-password`.
- "Sign in with an email link" leads to `/sign-in-link`.

## `/sign-in-link`: Sign-in link

```
(logo)                                     [English ▾]

Sign in with an email link
  Email     [                    ]
  [Send me a link]

Back to Sign in
```

- On submit, shows "If alice@example.org is known here, a sign-in link
  has been sent to it." instead of the form.

## `/access`: Access link

- Reached from the access link's `token` query parameter.
- On success, leads to My associations, signed in.
- An unknown token or a revoked link shows "This link is no longer
  valid." with a way to `/sign-in-link` to request a new one.

## `/forgot-password`: Forgot password

```
(logo)                                     [English ▾]

Forgot your password?
  Email     [                    ]
  [Send a reset link]

Back to Sign in
```

- On submit, shows "If alice@example.org has an account, a reset link
  has been sent to it." instead of the form.

## `/reset-password`: Reset password

```
(logo)                                     [English ▾]

Choose a new password
  New password  [                ]
  [Set password]
```

- Reached from the reset link's `token` query parameter.
- On success, leads to My associations, signed in.
- An unknown, expired, or already-used token shows "This link is no
  longer valid." with a way to `/forgot-password` to request a new
  one.

## `/signup`: Create an account

```
(logo)                                     [English ▾]

Create an account
  Display name  [                ]
  Email         [                ]
  Password      [                ]
  [Create account]

Already have an account? Sign in
```

- On success, shows "Check alice@example.org for a confirmation
  link." instead of signing in. A "Resend the email" action below it
  shows "Email sent." when clicked.
- When the email already has an account: "An account already exists
  for this email. Sign in instead."
- When the email was not invited (R19): "This email has not been
  invited. Ask a manager of your association to add you as a member."
- When the confirmation email cannot be sent: "We couldn't send the
  confirmation email. Try again later."

## `/verify-email`: Confirm email

- Reached from the confirmation link's `token` query parameter.
- On success, leads to My associations, signed in.
- An unknown, expired, or already-used token shows "This link is no
  longer valid." with a way back to `/signup` to request a new one.

## `/`, signed in: My associations

```
(logo)  My associations                                    Alice ▾

  Jardin partagé des Lilas                 MANAGER
    Thu 12 Nov, 10:00–13:00: this slot no longer takes place.  [OK]
    Thu 5 Nov, 10:00–13:00
    Sat 14 Nov, 10:00–13:00 ?  [Confirm]

  Repair Café Belleville                 VOLUNTEER
    No registration yet for the planning period, 2–25 Nov.
    Choose your slots

  Atelier vélo                           VOLUNTEER
    No upcoming registration.

[+ New association]
```

- "New association", below the list, leads to `/associations/new`.
- Each name leads to the association's Schedule.
- With no association: "You are not a member of any association yet."
- Sign out leads to Sign in.
- Each association lists its `upcoming` registrations; a proposed one
  is marked "?" and has "Confirm", which confirms it.
- Its `obsolete` registrations come first, each followed by "this slot
  no longer takes place." and "OK", which cancels it; it then no longer
  shows.
- R14: When the association has a planning period that ends today or
  later and the user has no registration in it (`registrations` is 0),
  the summary shows "No registration yet for the planning period,"
  with its dates, and "Choose your slots", which leads to the
  association's Schedule.
- Otherwise, with no upcoming registration: "No upcoming
  registration."
- The period's dates read as "2–25 Nov" within a month, "28 Oct – 25
  Nov" across months, and with years when they differ: "28 Dec 2026 –
  8 Jan 2027".

In French, e.g.:

```
Mes associations
  Jardin partagé des Lilas             RESPONSABLE
    jeu. 12 nov., 10:00–13:00 : ce créneau n'a plus lieu.  [OK]
    jeu. 5 nov., 10:00–13:00
    sam. 14 nov., 10:00–13:00 ?  [Confirmer]
  Repair Café Belleville                  BÉNÉVOLE
    Aucune inscription pour la période de planning, 2–25 nov.
    Choisir mes créneaux
  Atelier vélo                            BÉNÉVOLE
    Aucune inscription à venir.
```

## `/associations/new`: New association

```
(logo)  My associations › New association                  Alice ▾

New association
  Name  [                    ]
  [Create association]  Cancel
```

- Creating leads to the new association's Schedule; Cancel leads to My
  associations.

## `/associations/{id}/members`: Members

As a manager:

```
(logo)  Jardin partagé des Lilas › Members                 Alice ▾

                                                  [+ Add a member]
  Alice                                        MANAGER   ✎
  alice@example.org
  Bruno                                      VOLUNTEER   ✎
  bruno@example.org
  Chloé  not joined yet                      VOLUNTEER   ✎
  chloe@example.org
  David  not joined yet                      VOLUNTEER   ✎
  david@example.org
  Emma                                       VOLUNTEER   ✎
  emma@example.org
  Show all 7 members
```

- Members are listed managers first, then by display name.
- The first 5 members show; "Show all 7 members" shows the others.
  With 5 members or fewer, all show and the link does not.
- A member whose email is not confirmed shows "not joined yet".
- "Add a member" opens the dialog "Add a member": Display name, Email,
  Role (Volunteer by default), [Add member]. Adding a member shows
  "Chloé added."; an existing member shows "Chloé is already a member."
- The edit icon on Chloé, named "Edit Chloé", opens the dialog:

```
┌ Chloé ───────────────────────────────────────── ✕ ┐
│ chloe@example.org                                 │
│ Role [Volunteer ▾]                                │
│ [Save]  Cancel                                    │
│                                                   │
│ SIGN-IN LINK                                      │
│ [Send link]  Revoke link                          │
│                                                   │
│ Remove from the association                       │
└───────────────────────────────────────────────────┘
```

- Save with another role changes it and shows "Chloé is now manager.";
  with the same role, it closes the dialog and changes nothing.
  Demoting the last manager shows "An association keeps at least one
  manager." and changes nothing.
- "Revoke link" shows only for a member with an access link; it asks
  "Revoke Chloé's sign-in link?" with [Revoke]; confirming revokes it
  and shows "Chloé's sign-in link is revoked."
- "Send link" asks "Send Chloé's sign-in link by email?" with [Send];
  confirming sends it (R26) and shows "Chloé's sign-in link is sent."
  When the email cannot be sent: "We couldn't send Chloé's sign-in
  link. Try again later."
- "Remove from the association" asks "Remove Chloé from the
  association? Their upcoming registrations are cancelled." with
  [Remove]; confirming removes Chloé (R28) and shows "Chloé is removed."
  Removing the last manager shows "An association keeps at least one
  manager." and changes nothing. A manager who removes themself is
  led to My associations.
- A volunteer sees the members and their roles, without "Add a member"
  and without the edit icons.
- Signed out, every page but `/signup`, `/verify-email`,
  `/forgot-password`, `/reset-password`, `/sign-in-link` and `/access`
  shows Sign in.

In French, e.g.:

```
Mes associations
  Jardin partagé des Lilas             RESPONSABLE
  Repair Café Belleville                  BÉNÉVOLE
```
