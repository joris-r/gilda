# Operations

## General

The screens run every operation on the server.

- [refused] A refused operation changes nothing.
- [signed-out] Signed out, every operation but Create account, Confirm
  email, Resend confirmation, Request password reset, Reset password,
  Sign in, Request access link, Sign in by access link and Sign out:
  refused.
- [unknown-association] An operation on an association that does not
  exist, or of which the signed-in user is not a member: refused.

## Create account

- [created] No user has this email, and `INVITATION_ONLY` is not
  `true` or the email is the superuser's: a user is stored with the
  display name, email and password, not signed in.
- [claimed] A user without a password has this email: that user gets
  the password and the display name, and keeps their memberships.
- [confirmation] After /core/operations/create-account/created or
  /core/operations/create-account/claimed: an EmailVerificationToken is
  created for the user, replacing their previous one, and an email
  sent to them with a link to `/verify-email?token=<token>`.
- [language] The email is in the interface's language, as
  /ui/language/emails:

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
- [exists] A user with a password has this email: refused.
- [not-invited] No user has this email, `INVITATION_ONLY` is `true`,
  and the email is not the superuser's: refused.
- [short-password] Password of fewer than 8 characters: refused.
- [malformed] A field missing, or an email that is not valid: refused.
- [not-sent] The email cannot be sent: refused.

## Confirm email

- [confirmed] Token of a pending, unexpired EmailVerificationToken:
  - the user's `email_verified_at` is set, and the token deleted;
  - the user is signed in, as /core/operations/sign-in/new-session.
- [invalid] Token unknown, expired or already used: refused.

## Resend confirmation

- [resent] A user with this email exists and `email_verified_at` is
  null: an email is sent as /core/operations/create-account/confirmation,
  in the language of /core/operations/create-account/language.
- [ignored] Otherwise: nothing is sent.
- [answer] It succeeds in every case, also when the email cannot be
  sent.

## Request password reset

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
- [malformed] An email missing or not valid: refused.
- [answer] Otherwise, it succeeds in every case, also when the email
  cannot be sent.

## Reset password

- [reset] Token of a pending, unexpired PasswordResetToken, password
  of at least 8 characters:
  - the user's password is replaced, their `email_verified_at` set if
    null, and the token deleted;
  - the user is signed in, as /core/operations/sign-in/new-session;
    their other sessions stay signed in.
- [invalid] Token unknown, expired or already used: refused.
- [short-password] Password of fewer than 8 characters: refused.

## Delete account

- [deleted] Signed in:
  - the user's `deleted_at` is set, their email and password set to
    null, and their tokens and AccessLink deleted;
  - all their sessions are signed out;
  - each of their memberships ends.
- [last-manager] In an association where the user was the only
  manager, every remaining member becomes a manager.

## Sign in

- [signed-in] Email of a user whose email is confirmed, and their
  password: the user is signed in.
- [new-session] On success, the `session` cookie set holds a new
  value, and the session ID the request came with, if any, no longer
  authenticates.
- [wrong] Email unknown, without a password, not confirmed, or wrong
  password: refused, the same way in every case.

## Request access link

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
- [malformed] An email missing or not valid: refused.
- [answer] Otherwise, it succeeds in every case, also when the email
  cannot be sent.

## Sign in by access link

- [signed-in] Token of an AccessLink:
  - the user's `email_verified_at` is set if null;
  - the user is signed in, as /core/operations/sign-in/new-session;
    the link stays usable.
- [invalid] Token unknown, or of a revoked link: refused.

## Revoke my access link

- [revoked] Signed in:
  - the user's AccessLink, if any, is deleted;
  - the sessions it signed in no longer authenticate.

## Sign out

- [signed-out] Later requests are signed out.

## Create association

- [created] Free slug: an association is stored with the name and
  slug, and the signed-in user becomes its manager.
- [malformed-slug] Slug without the format of
  /core/model/association/slug-format: refused.
- [taken] Slug taken, or `new`: refused.

## Update association

Changes the name or the slug.

- [renamed] A name: the association takes it; its slug is unchanged.
- [new-slug] A slug, free or the association's own: the association
  takes it; the former slug no longer leads to it, and another
  association can take it.
- [silent] Its members are not told.
- [malformed-slug] Slug without the format of
  /core/model/association/slug-format: refused.
- [taken] Slug taken by another association, or `new`: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Delete association

- [deleted] The association and its memberships are erased.
- [silent] Its members stay users, in their other associations if
  any, and are not told.
- [volunteer] Signed-in user a volunteer: refused.

## Add member

- [new-user] No user has this email: a user without a password is
  stored with the display name and email, and becomes a member with
  the role.
- [existing-user] A user has this email: that user becomes the member,
  their display name unchanged.
- [already] That user is already a member: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Change role

- [changed] The member takes the role.
- [last-manager] It would leave the association without a manager:
  refused.
- [not-member] The user is not a member: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Remove member

- [removed] The membership ends. A manager may remove themself.
- [last-manager] It would leave the association without a manager:
  refused.
- [not-member] The user is not a member: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Send access link

- [sent] The member is sent the email of
  /core/operations/request-access-link/sent, in the language of
  /core/operations/create-account/language set by the manager's
  request, as /core/operations/request-access-link/same.
- [not-member] The user is not a member: refused.
- [not-sent] The email cannot be sent: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Revoke access link

- [revoked] The member's AccessLink is revoked, as
  /core/operations/revoke-my-access-link/revoked, in every association
  they belong to, also when they have none.
- [not-member] The user is not a member: refused.
- [volunteer] Signed-in user a volunteer: refused.
