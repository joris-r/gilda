# API

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

## Errors

- Error responses are JSON: `{"error": "<message>"}`.
- 400: the body is not valid JSON, or a field is missing, empty or
  invalid.
