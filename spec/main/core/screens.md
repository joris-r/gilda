# Screens

## `/`, signed out: Sign in

```
(logo)                                     [English ▾]

Sign in
  Email     [                    ]
  Password  [                    ]
  [Sign in]

No account yet? Create an account
```

- Wrong credentials show "Wrong email or password." under the form.
- "Create an account" leads to `/signup`.

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

- On success, the user is signed in and sees My associations.
- When the email already has an account: "An account already exists
  for this email. Sign in instead."

## `/`, signed in: My associations

```
(logo)                         Alice  Sign out  [English ▾]

My associations
  Jardin partagé des Lilas                 MANAGER
  Repair Café Belleville                 VOLUNTEER

Create an association
  Name  [                    ]
  [Create association]
```

- Each name leads to the association's page; creating one leads to the
  new association's page.
- With no association: "You are not a member of any association yet."
- Sign out leads to Sign in.

## `/associations/{id}`: Association

As a manager:

```
(logo)                         Alice  Sign out  [English ▾]

← My associations
Jardin partagé des Lilas
Schedule  Opening hours

Members
  Alice                                  MANAGER  Change role
  alice@example.org
  Bruno                                VOLUNTEER  Change role
  bruno@example.org
  Chloé  no account                    VOLUNTEER  Change role
  chloe@example.org

Add a member
  Display name [          ]  Email [          ]
  Role [Volunteer ▾]
  [Add member]
```

- "Schedule" and "Opening hours" lead to those pages of the
  association.
- Members are listed managers first, then by display name.
- "Change role" on Bruno replaces his line's actions with
  "Make Bruno manager? [Confirm] Cancel"; Confirm changes the role
  and shows "Bruno is now manager."
- Demoting the last manager shows "An association keeps at least one
  manager." and changes nothing.
- Adding a member shows "Chloé added."; an existing member shows
  "Chloé is already a member."
- A volunteer sees the members and their roles, without "Change role"
  and without the Add a member form.
- Signed out, every page but `/signup` shows Sign in.

In French, e.g.:

```
Mes associations
  Jardin partagé des Lilas             RESPONSABLE
  Repair Café Belleville                  BÉNÉVOLE
```
