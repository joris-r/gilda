# Operations

## General

The screens run every operation on the server: an input `user` is
the signed-in user of the request, and an input `association` the
association of the screen.

- [refused] A refused operation changes nothing.
- [malformed] An input other than `user` and `association` missing or
  not of its type, a display name or a name that is empty, or an email
  that is not valid: refused.
- [signed-out] Signed out, an operation with an input `user`:
  refused.
- [unknown-association] An input `association` that does not exist:
  refused.

## Initial state

- [empty] No user, token, link, session, association or membership;
  the configuration as the environment gives it.

## Create account

Inputs:
- `display_name: string`
- `email: string`
- `password: string`

Cases:
1. [short-password] Password of fewer than 8 characters: refused.
2. [not-invited] No user has this email, `invitation_only`, and the
   email is not the superuser's: refused.
3. [exists] A user with a password has this email: refused.
4. [not-sent] The email of /core/operations/create-account/confirmation
   cannot be sent: refused.
5. [created] No user has this email: a user is stored with the display
   name, email and password, email not verified, not deleted, not
   signed in.
6. [claimed] Otherwise, a user without a password has this email: that
   user gets the password and the display name, and keeps their
   memberships.

Then:
- [confirmation] After /core/operations/create-account/created or
  /core/operations/create-account/claimed: an EmailVerificationToken
  expiring 24 hours later is stored for the user, replacing their
  previous one, and /contents/confirmation-email is sent to them with
  a link to `/verify-email?token=<token>`.
  - [language] The email is in the interface's language, as
    /ui/language/emails.

## Confirm email

Inputs:
- `token: string`

Cases:
- [invalid] Token of no EmailVerificationToken, or of an expired one:
  refused.

Then:
- [confirmed] After no refusal:
  - the user's `email_verified_at` is set to now, and the token
    deleted;
  - the user is signed in, as /core/operations/sign-in/new-session.

## Resend confirmation

Inputs:
- `email: string`

Cases:
- [resent] A user with this email exists and `email_verified_at` is
  none: an email is sent as
  /core/operations/create-account/confirmation, in the language of
  /core/operations/create-account/language.
  - [answer] It succeeds also when the email cannot be sent.
- [ignored] Otherwise: nothing is sent.

## Request password reset

Inputs:
- `email: string`

Cases:
- [sent] A user with this email has a password: a PasswordResetToken
  expiring 1 hour later is stored for them, replacing their previous
  one, and /contents/password-reset-email is sent to them with a link
  to `/reset-password?token=<token>`, in the language of
  /core/operations/create-account/language.
  - [answer] It succeeds also when the email cannot be sent.
- [ignored] Otherwise: nothing is sent.

## Check reset token

Whether a reset link can still be used.

Inputs:
- `token: string`

Cases:
- [valid] Token of a PasswordResetToken that is not expired: answers
  valid.
- [invalid] Otherwise: answers invalid.

## Reset password

Inputs:
- `token: string`
- `password: string`

Cases:
1. [short-password] Password of fewer than 8 characters: refused.
2. [invalid] Token of no PasswordResetToken, or of an expired one:
   refused.

Then:
- [reset] After no refusal:
  - the user's password is replaced, their `email_verified_at` set to
    now if none, and the token deleted;
  - the user is signed in, as /core/operations/sign-in/new-session;
    their other sessions stay.

## Delete account

Inputs:
- `user: /core/model/user`

Cases:
- [deleted] The user's `deleted_at` is set to now, their email and
  password to none, their tokens, AccessLink and sessions deleted, and
  each of their memberships ends.
  - [last-manager] In an association where the user was the only
    manager, every remaining member becomes a manager.

## Sign in

Inputs:
- `email: string`
- `password: string`

Cases:
- [wrong] Email of no user, of a user without a password or whose
  `email_verified_at` is none, or wrong password: refused, the same
  way in every case.

Then:
- [signed-in] After no refusal: the user is signed in.
  - [new-session] A session without access link is stored for the
    user, with an id no session has; the `session` cookie set holds
    it, and the session the request came with, if any, is deleted.

## Request access link

Inputs:
- `email: string`

Cases:
- [sent] A user with this email exists, with or without a password:
  /contents/sign-in-link-email is sent to them with their AccessLink,
  stored, if they have none and the email can be sent, as a link to
  `/access?token=<token>`, in the language of
  /core/operations/create-account/language.
  - [same] A user who already has an AccessLink is sent the same
    link.
  - [answer] It succeeds also when the email cannot be sent.
  - [unsent] When the email cannot be sent, a user who had no
    AccessLink still has none.
- [ignored] Otherwise: nothing is sent.

## Sign in by access link

Inputs:
- `token: string`

Cases:
- [invalid] Token of no AccessLink: refused.

Then:
- [signed-in] After no refusal:
  - the user's `email_verified_at` is set to now if none;
  - the user is signed in, as /core/operations/sign-in/new-session,
    the session's access link being this one; the link stays.

## Revoke my access link

Inputs:
- `user: /core/model/user`

Cases:
- [revoked] The user has an AccessLink: it is deleted, with the
  sessions it opened.
- [none] The user has no AccessLink: nothing changes; returns that
  there was none.

## Sign out

Cases:
- [signed-out] The session the request came with, if any, is deleted.

## Create association

Inputs:
- `user: /core/model/user`
- `name: string`
- `slug: string`

Cases:
- [malformed-slug] Slug without the format of
  /core/model/association/slug-format: refused.
- [taken] Slug of an association, or `new`: refused.

Then:
- [created] After no refusal: an association is stored with the name,
  the slug and the timezone, and the user becomes its manager.

## Update association

Changes the name or the slug.

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `name: optional string`
- `slug: optional string`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [malformed-slug] Slug given, without the format of
   /core/model/association/slug-format: refused.
3. [taken] Slug given, of another association or `new`: refused.

Then:
- [changed] After no refusal:
  - [renamed] the association takes the name given, if any;
  - [new-slug] the association takes the slug given, if any; its
    former slug no longer leads to it, and another association can
    take it;
  - [silent] its members are not told.

## Delete association

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [deleted] Otherwise: the association and its memberships are
   erased.
   - [silent] Its members stay users, in their other associations if
     any, and are not told.

## Add member

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `display_name: string`
- `email: string`
- `role: one of manager, volunteer`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [already] A member of the association has this email: refused.
3. [existing-user] A user has this email: that user becomes a member
   with the role, their display name unchanged.
4. [new-user] Otherwise: a user without a password is stored with the
   display name and email, email not verified, and becomes a member
   with the role.

## Change role

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `member: /core/model/user`
- `role: one of manager, volunteer`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [not-member] The member is not a member of the association:
   refused.
3. [last-manager] The member is the only manager and the role is
   `volunteer`: refused.

Then:
- [changed] After no refusal: the member takes the role.

## Remove member

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `member: /core/model/user`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [not-member] The member is not a member of the association:
   refused.
3. [last-manager] The member is the only manager: refused.

Then:
- [removed] After no refusal: the member's membership ends, also when
  the member is the user.

## Send access link

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `member: /core/model/user`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [not-member] The member is not a member of the association:
   refused.
3. [not-sent] The email cannot be sent: refused.

Then:
- [sent] After no refusal: the member is sent the email of
  /core/operations/request-access-link/sent, in the language of
  /core/operations/create-account/language set by the user's
  request, as /core/operations/request-access-link/same.

## Revoke access link

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `member: /core/model/user`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [not-member] The member is not a member of the association:
   refused.

Then:
- [revoked] After no refusal, the member having an AccessLink: it is
  revoked, as /core/operations/revoke-my-access-link/revoked, in every
  association they belong to.
- [none] After no refusal, the member having no AccessLink: nothing
  changes; returns that there was none.

## Migrate slugs

Trigger: once, when slugs were introduced.

Cases:
- [legacy] Each association gets the slug derived from its name,
  followed by `-2`, `-3`… when taken or `new`, the whole cut to keep
  /core/model/association/slug-format.
