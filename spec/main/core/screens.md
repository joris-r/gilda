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
  has been sent to it." instead of the form, whether or not such a user
  exists, and when the email cannot be sent.
- R24: When a user with this email exists, with or without a password,
  an email is sent to it with their AccessLink, created if they have
  none, as a link to `/access?token=…`, in the language R20 sets:

  ```
  Subject: Your sign-in link

  Sign in by opening this link. Keep this email: the link stays valid
  until you revoke it.

  https://…/access?token=…
  ```

  ```
  Subject: Votre lien de connexion

  Connectez-vous en ouvrant ce lien. Conservez cet e-mail : le lien
  reste valable jusqu'à ce que vous le révoquiez.

  https://…/access?token=…
  ```
- R25: A user who already has an AccessLink is sent the same link.
- No email is sent to an unknown email.
- A missing or invalid email shows the generic error message.

## `/access`: Access link

- Reached from the access link's `token` query parameter.
- On success, sets the user's email_verified_at if still null, signs
  them in, as Sign in does (R16), and leads to My associations. The
  link stays usable.
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
  has been sent to it." instead of the form, whether or not such a user
  exists, and when the email cannot be sent.
- R21: When a user with this email has a password, a
  PasswordResetToken is created and an email sent to it, with a link
  to `/reset-password?token=…`, in the language R20 sets:

  ```
  Subject: Reset your password

  Choose a new password by opening this link, valid for one hour:

  https://…/reset-password?token=…
  ```

  ```
  Subject: Réinitialisez votre mot de passe

  Choisissez un nouveau mot de passe en ouvrant ce lien, valable une heure :

  https://…/reset-password?token=…
  ```
- No email is sent to a user without a password, nor to an unknown
  email.
- A missing or invalid email shows the generic error message.

## `/reset-password`: Reset password

```
(logo)                                     [English ▾]

Choose a new password
  New password  [                ]
  [Set password]
```

- Reached from the reset link's `token` query parameter.
- R22: On success, replaces the token's user's password, sets their
  email_verified_at if still null, deletes the token, signs the user
  in, as Sign in does (R16), and leads to My associations. The user's
  other sessions stay signed in.
- An unknown, expired, or already-used token shows "This link is no
  longer valid." with a way to `/forgot-password` to request a new
  one, in place of the form when the page opens, and on submit.
- Opening the link leaves the token usable.
- A password with fewer than 8 characters shows the generic error
  message; the token stays usable.

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

- On success, creates the user with this password and shows "Check
  alice@example.org for a confirmation link." instead of the form,
  signed out.
- R2: When a user without a password already has this email, that user
  gets the password and the given display name, and keeps their
  memberships.
- R9: On success, an EmailVerificationToken is created and a
  confirmation email sent to it, with a link to `/verify-email?token=…`.
- R20: The confirmation email is in the interface's language:

  ```
  Subject: Confirm your email

  Confirm your email by opening this link:

  https://…/verify-email?token=…
  ```

  ```
  Subject: Confirmez votre adresse e-mail

  Confirmez votre adresse e-mail en ouvrant ce lien :

  https://…/verify-email?token=…
  ```
- When a user with this email has a password: "An account already
  exists for this email. Sign in instead."
- R19: When `INVITATION_ONLY` is `true`, unless a user without a
  password already has this email, or it is the superuser's (see
  `POST /api/session`): "This email has not been invited. Ask a manager
  of your association to add you as a member."; nothing is saved.
- R10: When the confirmation email cannot be sent: "We couldn't send
  the confirmation email. Try again later."; nothing is saved.
- A password has at least 8 characters. A shorter one, or a missing or
  invalid field, shows the generic error message; nothing is saved.
- "Resend the email", below the confirmation message, shows "Email
  sent." It sends a new confirmation email (R8, R20) when this email's
  user is still unconfirmed. The screen shows the same whether or not
  it does, and when that email cannot be sent.

## `/verify-email`: Confirm email

- Reached from the confirmation link's `token` query parameter.
- On success, sets email_verified_at on the token's user, deletes the
  token, signs the user in, as Sign in does (R16), and leads to My
  associations.
- An unknown, expired, or already-used token shows "This link is no
  longer valid." with a way back to `/signup` to request a new one.
- Fetching the link without running the page leaves the token usable.

## `/`, signed in: My associations

```
(logo)  My associations                                    Alice ▾

  Jardin partagé des Lilas                 MANAGER
    Thu 12 Nov, 10:00–13:00  Alice: this slot no longer takes place.  [OK]
    Thu 5 Nov, 10:00–13:00  Alice
    Sat 14 Nov, 10:00–13:00  Alice ?  [Confirm]

  Repair Café Belleville                 VOLUNTEER
    No registration yet for the planning period, 2–25 Nov.
    Choose your slots

  Atelier vélo                           VOLUNTEER
    No upcoming registration.

[+ New association]
```

- "New association", below the list, leads to `/association/new`.
- Each name leads to the association's Schedule.
- With no association: "You are not a member of any association yet."
- Sign out leads to Sign in.
- Each association lists the user's registrations there:
  - R31: first the obsolete ones dated today or later, each followed
    by "this slot no longer takes place." and "OK", which cancels it
    (R7); it then no longer shows;
  - R12: then those dated today or later and not obsolete: every
    proposed one, and the confirmed ones up to the later of 27 days
    after today and, when the association has a planning period, its
    last date;
  - each group sorted by date, then start.
- A proposed registration is marked "?" and has "Confirm", which
  confirms it (R7).
- Each registration shows its date and times, then its display name,
  then its action. The name looks as on the Schedule, and the
  registration takes the Schedule's colours: green when confirmed,
  orange when proposed, red when obsolete. (Look not testable.)
- R13: A registration in the period is one of the user's, confirmed
  or proposed, not obsolete, dated within the period, both dates
  included.
- R14: When the association has a planning period that ends today or
  later and the user has no registration in it, the summary shows "No
  registration yet for the planning period," with its dates, and
  "Choose your slots", which leads to the association's Schedule.
- Otherwise, with no upcoming registration (R12): "No upcoming
  registration."
- An action that fails shows the generic error.
- The period's dates read as "2–25 Nov" within a month, "28 Oct – 25
  Nov" across months, and with years when they differ: "28 Dec 2026 –
  8 Jan 2027".

In French, e.g.:

```
Mes associations
  Jardin partagé des Lilas             RESPONSABLE
    jeu. 12 nov., 10:00–13:00  Alice : ce créneau n'a plus lieu.  [OK]
    jeu. 5 nov., 10:00–13:00  Alice
    sam. 14 nov., 10:00–13:00  Alice ?  [Confirmer]
  Repair Café Belleville                  BÉNÉVOLE
    Aucune inscription pour la période de planning, 2–25 nov.
    Choisir mes créneaux
  Atelier vélo                            BÉNÉVOLE
    Aucune inscription à venir.
```

## `/association/new`: New association

```
(logo)  My associations › New association                  Alice ▾

New association
  Name                    [Repair Café Belleville  ]
  Association identifier  /association/[repair-cafe-belleville  ]
  [Create association]  Cancel
```

- The field for the slug is named "Association identifier".
- R35: Until the user edits Association identifier, it follows Name: lowercase,
  without accents, each run of other characters becoming one hyphen,
  without a leading or trailing hyphen, cut to 50 characters.
- [Create association] is enabled only when both fields are not empty.
- A malformed slug shows "Use only lowercase letters, digits and
  hyphens, starting and ending with a letter or a digit."; a taken one
  shows "This association identifier is already taken."
- Creating makes the user its manager and leads to the new association's
  Schedule; Cancel leads to My associations.

## `/association/{slug}/members`: Members

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

  Rename the association
  Change the association identifier
  Delete the association
```

- Members are listed managers first, then by display name.
- The first 5 members show; "Show all 7 members" shows the others.
  With 5 members or fewer, all show and the link does not.
- A member whose email is not confirmed shows "not joined yet".
- "Add a member" opens the dialog "Add a member": Display name, Email,
  Role (Volunteer by default), [Add member]. Adding a member shows
  "Chloé added."; an existing member shows "Chloé is already a member."
  - R3: When a user already has this email, that user becomes the
    member; their display name is left unchanged.
  - Otherwise a new user without a password is created.
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
  (R23) and shows "Chloé's sign-in link is revoked."
- "Send link" asks "Send Chloé's sign-in link by email?" with [Send];
  confirming sends it and shows "Chloé's sign-in link is sent."
  When the email cannot be sent: "We couldn't send Chloé's sign-in
  link. Try again later."
  - R26: Chloé is sent the email of R24, in the language R20 sets
    from the manager's request; R25 applies.
- "Remove from the association" asks "Remove Chloé from the
  association? Their upcoming registrations are cancelled." with
  [Remove]; confirming removes Chloé (R28) and shows "Chloé is removed."
  Removing the last manager shows "An association keeps at least one
  manager." and changes nothing. A manager who removes themself is
  led to My associations.
- "Rename the association" opens the dialog:

```
┌ Rename the association ───────────────────────── ✕ ┐
│ Name [Jardin partagé des Lilas ]                   │
│ [Save]  Cancel                                     │
└────────────────────────────────────────────────────┘
```

- [Save] is enabled only when Name is not empty. Saving another name
  changes it, updates the header and shows "The association is now
  Jardin des Lilas."; the same name closes the dialog and changes
  nothing. The slug stays unchanged, and the members are not told.
- "Change the association identifier" opens the dialog:

```
┌ Change the association identifier ──────────────────────────── ✕ ┐
│ Association identifier /association/[jardin-partage-des-lilas ]   │
│ [Save]  Cancel                                                    │
└───────────────────────────────────────────────────────────────────┘
```

- [Save] is enabled only when Association identifier is not empty. Saving another
  slug changes it, moves the screen to the new URL and shows "The association
  identifier is now jardin-des-lilas."; the same slug closes the dialog
  and changes nothing. A malformed or taken slug shows the same message
  as on New association. The members are not told.
  - R36: Once the slug has changed, the former slug no longer leads to
    the association, and another association can take it.
- "Delete the association" opens the confirmation:

```
┌───────────────────────────────────────────────────┐
│ Delete Jardin partagé des Lilas? Its schedule and │
│ its members' registrations are erased. This       │
│ cannot be undone.                                 │
│ Type the association's name to confirm [        ] │
│ [Delete]  Cancel                                  │
└───────────────────────────────────────────────────┘
```

- [Delete] is enabled only when the field holds exactly the
  association's name. Confirming deletes it, leads to My
  associations and shows "Jardin partagé des Lilas is deleted."
  - R34: Everything the association holds is erased: its memberships and
    what its domains keep (for planning: its slots, closures, planning
    period, preferences, absences, notes, share link and registrations).
    Its members stay users, in their other associations if any, and are
    not told.
- A volunteer sees the members and their roles, without "Add a
  member", without the edit icons and without "Rename the association",
  "Change the association identifier" and "Delete the association".
- A screen of an association whose slug is unknown, or of which the
  user is not a member, shows "This association does not exist or you
  are not a member." with a way to My associations.
- Signed out, every screen but `/signup`, `/verify-email`,
  `/forgot-password`, `/reset-password`, `/sign-in-link` and `/access`
  shows Sign in.

In French, e.g.:

```
Mes associations
  Jardin partagé des Lilas             RESPONSABLE
  Repair Café Belleville                  BÉNÉVOLE
```
