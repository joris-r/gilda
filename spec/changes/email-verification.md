# email-verification: confirm an email before it can sign in

A user cannot sign in until they confirm the email they signed up with,
closing the window where someone else could take over a volunteer's
email (R2).

## Data model

- User
  - email_verified_at: timestamp, null until the email is confirmed
- EmailVerificationToken: a pending confirmation for a user
  - token: random, unique
  - user_id
  - expires_at: 24 hours after creation
  - R8: Creating a new token for a user deletes that user's previous
    one.

## Accounts

### POST /api/accounts

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

- Replaces: no longer signs the user in (drops `Set-Cookie` from the
  response).
- R9: On success, an EmailVerificationToken is created and a
  confirmation email sent to it, with a link to `/verify-email?token=…`.

### POST /api/accounts/verify

```http
POST /api/accounts/verify
Content-Type: application/json

{"token": "…"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"id": "0b6f…", "display_name": "Alice", "email": "alice@example.org"}
```

- Sets email_verified_at on the token's user, and deletes the token.
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
  null, sends a new confirmation email (replacing any pending token).
- Always 204, whether or not such a user exists, so the response
  cannot be used to probe for an email.

### POST /api/session

- Replaces R2's 401 case: fails the same way (401, same message) when
  the password is right but email_verified_at is null.

## Associations

### GET /api/associations/{id}

- Replaces: `has_account` is true only when the member has a password
  and email_verified_at is set — i.e. they can actually sign in.

## Screens

### `/signup`: Create an account

- Replaces: on success, shows "Check alice@example.org for a
  confirmation link." instead of signing in. A "Resend the email"
  action below it shows "Email sent." when clicked.

### `/verify-email`: Confirm email

```
(logo)                                     [English ▾]

Email confirmed. You can now sign in.
```

- Reached from the confirmation link's `token` query parameter.
- An unknown, expired, or already-used token shows "This link is no
  longer valid." with a way back to `/signup` to request a new one.

### `/associations/{id}`: Association

- Replaces: a member with `has_account: false` who does have a
  password (sign-up pending confirmation) shows "pending" instead of
  "no account".

## Technical

- Email is sent through SMTP:
  - Production: alwaysdata's SMTP relay, configured from environment
    variables.
  - Development and tests: Mailpit, run alongside PostgreSQL in
    `compose.yaml`, on non-default ports to avoid clashing with other
    projects' containers; backend tests query it over HTTP to read the
    sent email.
