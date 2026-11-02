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

                                                              [+]
  Jardin partagé des Lilas                 MANAGER
    Thu 5 Nov, 10:00–13:00
    Sat 14 Nov, 10:00–13:00 ?  [Confirm]

  Repair Café Belleville                 VOLUNTEER
    No registration yet for the planning period, 2–25 Nov.
    Choose your slots

  Atelier vélo                           VOLUNTEER
    No upcoming registration.
```

- "+", named "Create an association", shows the form:

```
Create an association
  Name  [                    ]
  [Create association]
```

- Each name leads to the association's Schedule; creating one leads to
  the new association's Schedule.
- With no association: "You are not a member of any association yet."
- Sign out leads to Sign in.
- Each association lists its `upcoming` registrations; a proposed one
  is marked "?" and has "Confirm", which confirms it.
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
    jeu. 5 nov., 10:00–13:00
    sam. 14 nov., 10:00–13:00 ?  [Confirmer]
  Repair Café Belleville                  BÉNÉVOLE
    Aucune inscription pour la période de planning, 2–25 nov.
    Choisir mes créneaux
  Atelier vélo                            BÉNÉVOLE
    Aucune inscription à venir.
```

## `/associations/{id}/members`: Members

As a manager:

```
(logo)  Jardin partagé des Lilas › Members                 Alice ▾

  Alice                     MANAGER  Change role  Send link  Revoke link
  alice@example.org
  Bruno                   VOLUNTEER  Change role  Send link  Revoke link
  bruno@example.org
  Chloé  not joined yet   VOLUNTEER  Change role  Send link
  chloe@example.org
  David  not joined yet   VOLUNTEER  Change role  Send link
  david@example.org
  Emma                    VOLUNTEER  Change role  Send link
  emma@example.org
  Show all 7 members

[Add a member]
```

- Members are listed managers first, then by display name.
- The first 5 members show; "Show all 7 members" shows the others.
  With 5 members or fewer, all show and the link does not.
- "Add a member" shows the form:

```
Add a member
  Display name [          ]  Email [          ]
  Role [Volunteer ▾]
  [Add member]
```

- "Change role" on Bruno replaces his line's actions with
  "Make Bruno manager? [Confirm] Cancel"; Confirm changes the role
  and shows "Bruno is now manager."
- Demoting the last manager shows "An association keeps at least one
  manager." and changes nothing.
- Adding a member shows "Chloé added."; an existing member shows
  "Chloé is already a member."
- A member whose email is not confirmed shows "not joined yet".
- "Revoke link" shows only for a member with an access link. On Bruno,
  it replaces his line's actions with "Revoke Bruno's sign-in link?
  [Confirm] Cancel"; Confirm revokes it and shows "Bruno's sign-in link
  is revoked."
- "Send link" on Chloé sends her access link (R26) and shows "Chloé's
  sign-in link is sent."; her line then shows "Revoke link". When the
  email cannot be sent: "We couldn't send Chloé's sign-in link. Try
  again later."
- A volunteer sees the members and their roles, without "Change role",
  "Send link", "Revoke link" and "Add a member".
- Signed out, every page but `/signup`, `/verify-email`,
  `/forgot-password`, `/reset-password`, `/sign-in-link` and `/access`
  shows Sign in.

In French, e.g.:

```
Mes associations
  Jardin partagé des Lilas             RESPONSABLE
  Repair Café Belleville                  BÉNÉVOLE
```
