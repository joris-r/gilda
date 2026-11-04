# API

## Accounts

### POST /api/accounts

Creates an account. The email must be confirmed (see
`POST /api/accounts/verify`) before it can sign in.

```http
POST /api/accounts
Content-Type: application/json

{"display_name": "Alice", "email": "alice@example.org", "password": "correct horse"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id": "0b6f…", "display_name": "Alice", "email": "alice@example.org"}
```

- R2: When a user without a password already has this email, the
  account is created on that user: it gets the password and the given
  display name, and keeps its memberships.
- R9: On success, an EmailVerificationToken is created and a
  confirmation email sent to it, with a link to `/verify-email?token=…`.
- R20: The confirmation email is in French when the request's
  `Accept-Language` header prefers French over English, in English
  otherwise:

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
- 409 when a user with a password already has this email.
- R19: When `INVITATION_ONLY` is `true`, 403 unless a user without a
  password already has this email, or it is the superuser's (see
  `POST /api/session`); nothing is saved.
- 400 when the password has fewer than 8 characters.
- R10: 503 when the confirmation email cannot be sent; nothing is
  saved.

### POST /api/accounts/verify

Confirms an email from its link's token.

```http
POST /api/accounts/verify
Content-Type: application/json

{"token": "…"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: session=…

{"id": "0b6f…", "display_name": "Alice", "email": "alice@example.org", "superuser": false}
```

- Sets email_verified_at on the token's user, deletes the token, and
  signs the user in, as `POST /api/session` does (R16).
- 404 when the token is unknown, expired, or already used.

### POST /api/accounts/verify/resend

```http
POST /api/accounts/verify/resend
Content-Type: application/json

{"email": "alice@example.org"}
```

```http
HTTP/1.1 204 No Content
```

- When a user with this email exists and email_verified_at is still
  null, sends a new confirmation email (replacing any pending token),
  in the language given by R20.
- Always 204, whether or not such a user exists, so the response
  cannot be used to probe for an email.

### POST /api/accounts/password-reset

Asks for a password reset link.

```http
POST /api/accounts/password-reset
Content-Type: application/json

{"email": "alice@example.org"}
```

```http
HTTP/1.1 204 No Content
```

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
- Always 204, as `POST /api/accounts/verify/resend`.

### POST /api/accounts/password-reset/confirm

Sets a new password from the link's token.

```http
POST /api/accounts/password-reset/confirm
Content-Type: application/json

{"token": "…", "password": "battery staple"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: session=…

{"id": "0b6f…", "display_name": "Alice", "email": "alice@example.org", "superuser": false}
```

- R22: Replaces the token's user's password, sets their
  email_verified_at if still null, deletes the token, and signs the
  user in, as `POST /api/session` does (R16). The user's other
  sessions stay signed in.
- 404 when the token is unknown, expired, or already used.
- 400 when the password has fewer than 8 characters; the token stays
  usable.

### DELETE /api/accounts/me

Deletes the signed-in user's account.

```http
DELETE /api/accounts/me
```

```http
HTTP/1.1 204 No Content
```

- R29: Sets deleted_at, sets email and password to null, deletes the
  user's tokens and AccessLink, signs out all their sessions, and ends
  each of their memberships (R28). Their email can then be used by a
  new user, through `POST /api/accounts` or
  `POST /api/associations/{id}/members`.
- R30: In an association where the user was the only manager, every
  remaining member becomes a manager.
- 401 when signed out.

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

{"id": "0b6f…", "display_name": "Alice", "email": "alice@example.org", "superuser": false}
```

- `superuser` is true when the user's email equals
  `SUPERUSER_EMAIL`, ignoring case; always false when that variable
  is unset.
- 401 when the email is unknown, has no account, the email is not
  confirmed, or the password is wrong; the response does not say
  which.
- R16: On success, the `session` cookie set holds a new value, and the
  session ID the request came with, if any, no longer authenticates.

### POST /api/access-link

Asks for the user's access link.

```http
POST /api/access-link
Content-Type: application/json

{"email": "chloe@example.org"}
```

```http
HTTP/1.1 204 No Content
```

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
- Always 204, as `POST /api/accounts/verify/resend`.

### POST /api/session/access-link

Signs in from an access link's token.

```http
POST /api/session/access-link
Content-Type: application/json

{"token": "…"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: session=…

{"id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "superuser": false}
```

- Sets the user's email_verified_at if still null, and signs them in,
  as `POST /api/session` does (R16). The link stays usable.
- 404 when the token is unknown or its link revoked.

### DELETE /api/access-link

Revokes the signed-in user's AccessLink (R23): 204, also when they
have none; 401 when signed out.

### GET /api/session

Returns the signed-in user, as `POST /api/session` does; 401 when
signed out.

### DELETE /api/session

Signs out: 204, and later requests are signed out.

## Associations

Every endpoint below requires a signed-in user: 401 otherwise.

### GET /api/associations

The associations the signed-in user is a member of, with their role and
what concerns them there.

```http
HTTP/1.1 200 OK
Content-Type: application/json

[{"id": "5c1e…", "name": "Jardin partagé des Lilas", "role": "manager",
  "upcoming": [
    {"id": "1d3a…", "user_id": "0b6f…", "display_name": "Alice", "status": "confirmed",
     "date": "2026-11-05", "start": "10:00", "end": "13:00"},
    {"id": "48be…", "user_id": "0b6f…", "display_name": "Alice", "status": "proposed",
     "date": "2026-11-14", "start": "10:00", "end": "13:00"}
  ],
  "obsolete": [
    {"id": "9f20…", "user_id": "0b6f…", "display_name": "Alice", "status": "confirmed",
     "date": "2026-11-12", "start": "10:00", "end": "13:00"}
  ],
  "planning_period": {"first": "2026-11-02", "last": "2026-11-25", "registrations": 2}},
 {"id": "9a2d…", "name": "Repair Café Belleville", "role": "volunteer",
  "upcoming": [], "obsolete": [], "planning_period": null}]
```

- Registrations are shown as `POST /api/associations/{id}/registrations`
  returns them, and only the signed-in user's.
- R12: `upcoming` holds the user's registrations dated today or later
  and not obsolete, sorted by date, then start:
  - every proposed one;
  - the confirmed ones up to the later of 27 days after today and, when
    the association has a planning period, its last date.
- R31: `obsolete` holds the user's obsolete registrations dated today
  or later, sorted by date, then start.
- R13: `planning_period` is `null` when the association has none; else
  `registrations` counts the user's confirmed and proposed
  registrations dated within the period, both dates included, and not
  obsolete.

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
  "timezone": "Europe/Paris",
  "role": "manager",
  "members": [
    {"user_id": "0b6f…", "display_name": "Alice", "email": "alice@example.org", "has_account": true, "email_verified": true, "access_link": true, "role": "manager"},
    {"user_id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "has_account": false, "email_verified": false, "access_link": false, "role": "volunteer"}
  ]
}
```

- `role` is the signed-in user's role.
- `access_link` is true when the member has an AccessLink.
- 404 when the association does not exist or the signed-in user is not
  a member.

### PATCH /api/associations/{id}

Renames the association. Managers only: 403 for a volunteer.

```http
PATCH /api/associations/5c1e…
Content-Type: application/json

{"name": "Jardin des Lilas"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"id": "5c1e…", "name": "Jardin des Lilas", "role": "manager"}
```

- Its members are not told.
- 404 when the association does not exist or the signed-in user is not
  a member.

### DELETE /api/associations/{id}

Deletes the association for good. Managers only: 403 for a volunteer.

- 204.
- R34: Everything the association holds is erased: its memberships and
  what its domains keep (for planning: its slots, closures, planning
  period, preferences, absences, notes, share link and registrations).
  Its members stay users, in their other associations if any, and are
  not told.
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

{"user_id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "has_account": false, "email_verified": false, "access_link": false, "role": "volunteer"}
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

{"user_id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "has_account": false, "email_verified": false, "access_link": false, "role": "manager"}
```

- 409 when it would leave the association without a manager (R1).
- 404 when the user is not a member.

### DELETE /api/associations/{id}/members/{user_id}

Removes a member from the association, ending their membership (R28).
Managers only: 403 for a volunteer.

- 204. A manager may remove themself.
- 409 when it would leave the association without a manager (R1).
- 404 when the user is not a member.

### POST /api/associations/{id}/members/{user_id}/access-link

Sends a member their access link. Managers only: 403 for a volunteer.

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"user_id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "has_account": false, "email_verified": false, "access_link": true, "role": "volunteer"}
```

- R26: Sends the member the email of R24, in the language R20 sets
  from the manager's request; R25 applies.
- 404 when the user is not a member.
- 503 when the email cannot be sent.

### DELETE /api/associations/{id}/members/{user_id}/access-link

Revokes a member's AccessLink (R23), in every association they belong
to. Managers only: 403 for a volunteer.

- 204, also when the member has none.
- 404 when the user is not a member.

## Errors

- Error responses are JSON: `{"error": "<message>"}`.
- 400: the body is not valid JSON, or a field is missing, empty or
  invalid.
