# users-associations: accounts, associations and their members

People create an account and sign in, create associations, and add
members to them, with or without an account. Replaces the health check.

## Pages

- New `spec/main/core/` folder, for the core domain:
  - `data-model.md`: the Data model section below.
  - `api.md`: the Accounts and Associations sections below, as its
    sections.
  - `screens.md`: the Screens section below.
- `interface.md` and `technical.md` stay at the root of `spec/main/`.

## Data model

- User
  - id: UUID
  - display_name: free text, not empty; may be a pseudonym
  - email: unique, compared ignoring case
  - password: optional; a user with a password has an account and can
    sign in, a user without one is only a member of associations
- Association
  - id: UUID
  - name: free text, not empty
- Membership: a user in an association, at most one per pair
  - role: `manager` or `volunteer`
  - R1: An association always has at least one manager.

## Accounts

### POST /api/accounts

Creates an account and signs it in.

```http
POST /api/accounts
Content-Type: application/json

{"display_name": "Alice", "email": "alice@example.org", "password": "correct horse"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json
Set-Cookie: session=…

{"id": "0b6f…", "display_name": "Alice", "email": "alice@example.org"}
```

- R2: When a user without a password already has this email, the
  account is created on that user: it gets the password and the given
  display name, and keeps its memberships.
- 409 when a user with a password already has this email.
- 400 when the password has fewer than 8 characters.

### POST /api/session

Signs in.

```http
POST /api/session
Content-Type: application/json

{"email": "alice@example.org", "password": "correct horse"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: session=…

{"id": "0b6f…", "display_name": "Alice", "email": "alice@example.org"}
```

- 401 when the email is unknown, has no account, or the password is
  wrong; the response does not say which.

### GET /api/session

Returns the signed-in user, as `POST /api/session` does; 401 when
signed out.

### DELETE /api/session

Signs out: 204, and later requests are signed out.

## Associations

Every endpoint below requires a signed-in user: 401 otherwise.

### GET /api/associations

The associations the signed-in user is a member of, with their role.

```http
HTTP/1.1 200 OK
Content-Type: application/json

[{"id": "5c1e…", "name": "Jardin partagé des Lilas", "role": "manager"}]
```

### POST /api/associations

```http
POST /api/associations
Content-Type: application/json

{"name": "Repair Café Belleville"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id": "9a2d…", "name": "Repair Café Belleville", "role": "manager"}
```

- The signed-in user becomes its manager.

### GET /api/associations/{id}

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "5c1e…",
  "name": "Jardin partagé des Lilas",
  "role": "manager",
  "members": [
    {"user_id": "0b6f…", "display_name": "Alice", "email": "alice@example.org", "has_account": true, "role": "manager"},
    {"user_id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "has_account": false, "role": "volunteer"}
  ]
}
```

- `role` is the signed-in user's role.
- 404 when the association does not exist or the signed-in user is not
  a member.

### POST /api/associations/{id}/members

Managers only: 403 for a volunteer.

```http
POST /api/associations/5c1e…/members
Content-Type: application/json

{"display_name": "Chloé", "email": "chloe@example.org", "role": "volunteer"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"user_id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "has_account": false, "role": "volunteer"}
```

- R3: When a user already has this email, that user becomes the
  member; their display name is left unchanged.
- Otherwise a new user without a password is created.
- 409 when that user is already a member.

### PATCH /api/associations/{id}/members/{user_id}

Changes a member's role. Managers only: 403 for a volunteer.

```http
PATCH /api/associations/5c1e…/members/77c0…
Content-Type: application/json

{"role": "manager"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"user_id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "has_account": false, "role": "manager"}
```

- 409 when it would leave the association without a manager (R1).
- 404 when the user is not a member.

### Errors

- Error responses are JSON: `{"error": "<message>"}`.
- 400: the body is not valid JSON, or a field is missing, empty or
  invalid.

## Screens

### `/`, signed out: Sign in

```
Gilda                                      [English ▾]

Sign in
  Email     [                    ]
  Password  [                    ]
  [Sign in]

No account yet? Create an account
```

- Wrong credentials show "Wrong email or password." under the form.
- "Create an account" leads to `/signup`.

### `/signup`: Create an account

```
Gilda                                      [English ▾]

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

### `/`, signed in: My associations

```
Gilda                          Alice  Sign out  [English ▾]

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

### `/associations/{id}`: Association

As a manager:

```
Gilda                          Alice  Sign out  [English ▾]

← My associations
Jardin partagé des Lilas

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

## Interface

Replaces the first rule of `interface.md` ("The interface is in English
by default."):

- The interface opens in French when the browser prefers French, in
  English otherwise; a choice made with the language selector wins.

New rules in `interface.md`:

- The interface follows the browser's light or dark preference.
- The accent colour is orange.

## Technical

New rules in `technical.md`:

- Every entity is identified by a UUID.
- Passwords are stored hashed with Argon2, never in clear.
- Sessions are server-side, stored in PostgreSQL; the browser keeps
  only a session identifier, in an `HttpOnly` cookie.
- The backend domain folder for the core domain is `core/`, replacing
  the `health/` example.

## Removed

- `status.md`: `GET /api/health` and the Status page.
