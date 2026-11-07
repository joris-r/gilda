# API

## Accounts

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
- 401 when the email is unknown, has no password, the email is not
  confirmed, or the password is wrong; the response does not say
  which.
- R16: On success, the `session` cookie set holds a new value, and the
  session ID the request came with, if any, no longer authenticates.

### GET /api/session

Returns the signed-in user, as `POST /api/session` does; 401 when
signed out.

### DELETE /api/session

Signs out: 204, and later requests are signed out.

## Associations

Every endpoint below requires a signed-in user: 401 otherwise.

### POST /api/associations

```http
POST /api/associations
Content-Type: application/json

{"name": "Repair Café Belleville", "slug": "repair-cafe-belleville"}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id": "9a2d…", "name": "Repair Café Belleville", "slug": "repair-cafe-belleville", "role": "manager"}
```

- 400 when the slug does not have the format of a slug.
- 409 when the slug is taken or is `new`.

### GET /api/associations/by-slug/{slug}

Returns what `GET /api/associations/{id}` returns.

- 404 when no association has this slug or the signed-in user is not a
  member.

### GET /api/associations/{id}

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "5c1e…",
  "name": "Jardin partagé des Lilas",
  "slug": "jardin-partage-des-lilas",
  "timezone": "Europe/Paris",
  "role": "manager",
  "members": [
    {"user_id": "0b6f…", "display_name": "Alice", "email": "alice@example.org", "has_account": true, "email_verified": true, "role": "manager"},
    {"user_id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "has_account": false, "email_verified": false, "role": "volunteer"}
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

{"user_id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "has_account": false, "email_verified": false, "role": "volunteer"}
```

- 409 when that user is already a member.

## Errors

- Error responses are JSON: `{"error": "<message>"}`.
- 400: the body is not valid JSON, or a field is missing, empty or
  invalid.
