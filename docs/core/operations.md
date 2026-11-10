# Operations

## General

JSON in and out. A user reads `{"id": "0b6f…", "display_name":
"Alice", "email": "alice@example.org", "superuser": false}`.

- [refused] A refused operation changes nothing and answers
  `{"error": "<message>"}`.
- The message of a refused operation is left to the implementation.
- [malformed] Body not valid JSON, or a field missing, empty or
  invalid: refused, 400.
- [signed-out] Signed out, every operation but Create account, Confirm
  email, Resend confirmation, Request password reset, Reset password,
  Sign in, Request access link, Sign in by access link, Sign out, Get
  shared association and Get shared schedule: refused, 401.
- [unknown-association] An operation on an association that does not
  exist, or of which the signed-in user is not a member: refused, 404.

## Create account

HTTP: `POST /api/accounts` with `{"display_name": "Alice", "email":
"alice@example.org", "password": "correct horse"}`.

- [created] No user has this email, and `INVITATION_ONLY` is not
  `true` or the email is the superuser's:
  - a user is stored with the display name, email and password;
  - answers 201 with `{"id": "0b6f…", "display_name": "Alice",
    "email": "alice@example.org"}`, not signed in.
- [claimed] A user without a password has this email:
  - that user gets the password and the display name, and keeps their
    memberships;
  - answers as /core/operations/create-account/created.
- [confirmation] After /core/operations/create-account/created or
  /core/operations/create-account/claimed: an EmailVerificationToken is
  created for the user, replacing their previous one, and an email
  sent to them with a link to `/verify-email?token=<token>`.
- [language] The email is in French when the request's
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
- [exists] A user with a password has this email: refused, 409.
- [not-invited] No user has this email, `INVITATION_ONLY` is `true`,
  and the email is not the superuser's: refused, 403.
- [short-password] Password of fewer than 8 characters: refused, 400.
- [not-sent] The email cannot be sent: refused, 503.

## Confirm email

HTTP: `POST /api/accounts/verify` with `{"token": "…"}`.

- [confirmed] Token of a pending, unexpired EmailVerificationToken:
  - the user's `email_verified_at` is set, and the token deleted;
  - the user is signed in, as /core/operations/sign-in/new-session;
  - answers 200 with the user.
- [invalid] Token unknown, expired or already used: refused, 404.

## Resend confirmation

HTTP: `POST /api/accounts/verify/resend` with `{"email":
"alice@example.org"}`.

- [resent] A user with this email exists and `email_verified_at` is
  null: an email is sent as /core/operations/create-account/confirmation,
  in the language of /core/operations/create-account/language.
- [ignored] Otherwise: nothing is sent.
- [answer] Answers 204 in every case.

## Request password reset

HTTP: `POST /api/accounts/password-reset` with `{"email":
"alice@example.org"}`.

- [sent] A user with this email has a password: a PasswordResetToken
  is created for them, replacing their previous one, and an email sent
  to them with a link to `/reset-password?token=<token>`, in the
  language of /core/operations/create-account/language:

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
- [ignored] Otherwise: nothing is sent.
- [answer] Answers 204 in every case.

## Reset password

HTTP: `POST /api/accounts/password-reset/confirm` with `{"token":
"…", "password": "battery staple"}`.

- [reset] Token of a pending, unexpired PasswordResetToken, password
  of at least 8 characters:
  - the user's password is replaced, their `email_verified_at` set if
    null, and the token deleted;
  - the user is signed in, as /core/operations/sign-in/new-session;
    their other sessions stay signed in;
  - answers 200 with the user.
- [invalid] Token unknown, expired or already used: refused, 404.
- [short-password] Password of fewer than 8 characters: refused, 400.

## Delete account

HTTP: `DELETE /api/accounts/me`.

- [deleted] Signed in:
  - the user's `deleted_at` is set, their email and password set to
    null, and their tokens and AccessLink deleted;
  - all their sessions are signed out;
  - each of their memberships ends;
  - answers 204.
- [last-manager] In an association where the user was the only
  manager, every remaining member becomes a manager.

## Sign in

HTTP: `POST /api/session` with `{"email": "alice@example.org",
"password": "correct horse"}`.

- [signed-in] Email of a user whose email is confirmed, and their
  password: answers 200 with the user.
- [new-session] On success, the `session` cookie set holds a new
  value, and the session ID the request came with, if any, no longer
  authenticates.
- [wrong] Email unknown, without a password, not confirmed, or wrong
  password: refused, 401, with the same answer in every case.

## Request access link

HTTP: `POST /api/access-link` with `{"email": "chloe@example.org"}`.

- [sent] A user with this email exists, with or without a password: an
  email is sent to them with their AccessLink, created if they have
  none, as a link to `/access?token=<token>`, in the language of
  /core/operations/create-account/language:

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
- [same] A user who already has an AccessLink is sent the same link.
- [ignored] No user has this email: nothing is sent.
- [answer] Answers 204 in every case.

## Sign in by access link

HTTP: `POST /api/session/access-link` with `{"token": "…"}`.

- [signed-in] Token of an AccessLink:
  - the user's `email_verified_at` is set if null;
  - the user is signed in, as /core/operations/sign-in/new-session;
    the link stays usable;
  - answers 200 with the user.
- [invalid] Token unknown, or of a revoked link: refused, 404.

## Revoke my access link

HTTP: `DELETE /api/access-link`.

- [revoked] Signed in:
  - the user's AccessLink, if any, is deleted;
  - the sessions it signed in no longer authenticate;
  - answers 204.

## Get session

HTTP: `GET /api/session`.

- [user] Signed in: answers 200 with the user.

## Sign out

HTTP: `DELETE /api/session`.

- [signed-out] Answers 204; later requests are signed out.

## Create association

HTTP: `POST /api/associations` with `{"name": "Repair Café
Belleville", "slug": "repair-cafe-belleville"}`.

- [created] Free slug:
  - an association is stored with the name and slug, and the
    signed-in user becomes its manager;
  - answers 201 with `{"id": "9a2d…", "name": "Repair Café
    Belleville", "slug": "repair-cafe-belleville", "role": "manager"}`.
- [malformed-slug] Slug without the format of
  /core/model/association/slug-format: refused, 400.
- [taken] Slug taken, or `new`: refused, 409.

## Get association

HTTP: `GET /api/associations/<id>`, or
`GET /api/associations/by-slug/<slug>`.

- [detail] Answers 200 with:

  ```json
  {
    "id": "5c1e…",
    "name": "Jardin partagé des Lilas",
    "slug": "jardin-partage-des-lilas",
    "timezone": "Europe/Paris",
    "role": "manager",
    "members": [
      {"user_id": "0b6f…", "display_name": "Alice", "email": "alice@example.org", "has_account": true, "email_verified": true, "access_link": true, "role": "manager"},
      {"user_id": "77c0…", "display_name": "Chloé", "email": "chloe@example.org", "has_account": false, "email_verified": false, "access_link": false, "role": "volunteer"}
    ]
  }
  ```

  - `role` is the signed-in user's role;
  - a member's `has_account` is true when they have a password,
    `email_verified` when their email is confirmed, `access_link` when
    they have an AccessLink.
- [by-slug] By slug: the association that has it now.

## Update association

HTTP: `PATCH /api/associations/<id>` with `{"name": "Jardin des
Lilas"}`, `{"slug": "jardin-des-lilas"}`, or both.

- [renamed] A name: the association takes it; its slug is unchanged.
- [new-slug] A slug, free or the association's own: the association
  takes it; the former slug no longer leads to it, and another
  association can take it.
- [answer] On success: answers 200 with the association, as
  /core/operations/create-association/created.
- [silent] Its members are not told.
- [neither] Neither a name nor a slug: refused, 400.
- [malformed-slug] Slug without the format of
  /core/model/association/slug-format: refused, 400.
- [taken] Slug taken by another association, or `new`: refused, 409.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Delete association

HTTP: `DELETE /api/associations/<id>`.

- [deleted] The association and its memberships are erased; answers
  204.
- [silent] Its members stay users, in their other associations if
  any, and are not told.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Add member

HTTP: `POST /api/associations/<id>/members` with `{"display_name":
"Chloé", "email": "chloe@example.org", "role": "volunteer"}`.

- [new-user] No user has this email:
  - a user without a password is stored with the display name and
    email, and becomes a member with the role;
  - answers 201 with the member, as in
    /core/operations/get-association/detail.
- [existing-user] A user has this email: that user becomes the member,
  their display name unchanged; answers as
  /core/operations/add-member/new-user.
- [already] That user is already a member: refused, 409.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Change role

HTTP: `PATCH /api/associations/<id>/members/<user_id>` with `{"role":
"manager"}`.

- [changed] The member takes the role; answers 200 with the member.
- [last-manager] It would leave the association without a manager:
  refused, 409.
- [not-member] The user is not a member: refused, 404.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Remove member

HTTP: `DELETE /api/associations/<id>/members/<user_id>`.

- [removed] The membership ends; answers 204. A manager may remove
  themself.
- [last-manager] It would leave the association without a manager:
  refused, 409.
- [not-member] The user is not a member: refused, 404.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Send access link

HTTP: `POST /api/associations/<id>/members/<user_id>/access-link`.

- [sent] The member is sent the email of
  /core/operations/request-access-link/sent, in the language of
  /core/operations/create-account/language set by the manager's
  request, as /core/operations/request-access-link/same; answers 200
  with the member.
- [not-member] The user is not a member: refused, 404.
- [not-sent] The email cannot be sent: refused, 503.
- [volunteer] Signed-in user a volunteer: refused, 403.

## Revoke access link

HTTP: `DELETE /api/associations/<id>/members/<user_id>/access-link`.

- [revoked] The member's AccessLink is revoked, as
  /core/operations/revoke-my-access-link/revoked, in every association
  they belong to; answers 204, also when they have none.
- [not-member] The user is not a member: refused, 404.
- [volunteer] Signed-in user a volunteer: refused, 403.
