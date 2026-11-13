# Operations

## General

The screens run every operation on the server, as the signed-in user
of the request.

- [refused] A refused operation changes nothing.
- [first] The cases of an operation are read in order, after those of
  General: the first one whose condition holds applies.
- [malformed] An input missing or not of its type, a display name or
  a name that is empty, or an email that is not valid: refused.
- [signed-out] Signed out, every operation but Create account, Confirm
  email, Resend confirmation, Request password reset, Check reset
  token, Reset password, Sign in, Request access link, Sign in by
  access link, Sign out, and the operations another domain opens
  signed in or not: refused.
- [unknown-association] An operation on an association that does not
  exist, or of which the signed-in user is not a member: refused.

## Initial state

- [empty] No user, token, link, session, association or membership;
  the configuration as the environment gives it.

## Create account

Inputs:
- `display_name: string`
- `email: string`
- `password: string`

Cases:
- [short-password] Password of fewer than 8 characters: refused.
- [not-invited] No user has this email, `invitation_only`, and the
  email is not the superuser's: refused.
- [exists] A user with a password has this email: refused.
- [not-sent] The email of /core/operations/create-account/confirmation
  cannot be sent: refused.
- [created] No user has this email: a user is stored with the display
  name, email and password, email not verified, not deleted, not
  signed in.
- [claimed] Otherwise, a user without a password has this email: that
  user gets the password and the display name, and keeps their
  memberships.
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
- [confirmed] Otherwise:
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
- [short-password] Password of fewer than 8 characters: refused.
- [invalid] Token of no PasswordResetToken, or of an expired one:
  refused.
- [reset] Otherwise:
  - the user's password is replaced, their `email_verified_at` set to
    now if none, and the token deleted;
  - the user is signed in, as /core/operations/sign-in/new-session;
    their other sessions stay.

## Delete account

Cases:
- [deleted] Signed in:
  - the user's `deleted_at` is set to now, their email and password
    to none, and their tokens, AccessLink and sessions deleted;
  - each of their memberships ends.
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
- [signed-in] Otherwise: the user is signed in.
  - [new-session] A session without access link is stored for the
    user, with an id no session has; the `session` cookie set holds
    it, and the session the request came with, if any, is deleted.

## Request access link

Inputs:
- `email: string`

Cases:
- [sent] A user with this email exists, with or without a password:
  /contents/sign-in-link-email is sent to them with their AccessLink,
  stored if they have none, as a link to `/access?token=<token>`, in
  the language of /core/operations/create-account/language.
  - [same] A user who already has an AccessLink is sent the same
    link.
  - [answer] It succeeds also when the email cannot be sent.
- [ignored] Otherwise: nothing is sent.

## Sign in by access link

Inputs:
- `token: string`

Cases:
- [invalid] Token of no AccessLink: refused.
- [signed-in] Otherwise:
  - the user's `email_verified_at` is set to now if none;
  - the user is signed in, as /core/operations/sign-in/new-session,
    the session's access link being this one; the link stays.

## Revoke my access link

Cases:
- [revoked] Signed in: the user's AccessLink, if any, is deleted, with
  the sessions it opened.

## Sign out

Cases:
- [signed-out] The session the request came with, if any, is deleted.

## Create association

Inputs:
- `name: string`
- `slug: string`

Cases:
- [malformed-slug] Slug without the format of
  /core/model/association/slug-format: refused.
- [taken] Slug of an association, or `new`: refused.
- [created] Otherwise: an association is stored with the name, the
  slug and the timezone, and the signed-in user becomes its manager.

## Update association

Changes the name or the slug.

Inputs:
- `name: optional string`
- `slug: optional string`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [malformed-slug] Slug given, without the format of
  /core/model/association/slug-format: refused.
- [taken] Slug given, of another association or `new`: refused.
- [changed] Otherwise:
  - [renamed] the association takes the name given, if any;
  - [new-slug] the association takes the slug given, if any; its
    former slug no longer leads to it, and another association can
    take it;
  - [silent] its members are not told.

## Delete association

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [deleted] Otherwise: the association and its memberships are erased.
  - [silent] Its members stay users, in their other associations if
    any, and are not told.

## Add member

Inputs:
- `display_name: string`
- `email: string`
- `role: one of manager, volunteer`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [already] A member of the association has this email: refused.
- [existing-user] A user has this email: that user becomes a member
  with the role, their display name unchanged.
- [new-user] Otherwise: a user without a password is stored with the
  display name and email, email not verified, and becomes a member
  with the role.

## Change role

Inputs:
- `user: /core/model/user`
- `role: one of manager, volunteer`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [not-member] The user is not a member: refused.
- [last-manager] The user is the only manager and the role is
  `volunteer`: refused.
- [changed] Otherwise: the member takes the role.

## Remove member

Inputs:
- `user: /core/model/user`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [not-member] The user is not a member: refused.
- [last-manager] The user is the only manager and the association has
  other members: refused.
- [removed] Otherwise: the membership ends. A manager may remove
  themself.

## Send access link

Inputs:
- `user: /core/model/user`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [not-member] The user is not a member: refused.
- [not-sent] The email cannot be sent: refused.
- [sent] Otherwise: the member is sent the email of
  /core/operations/request-access-link/sent, in the language of
  /core/operations/create-account/language set by the manager's
  request, as /core/operations/request-access-link/same.

## Revoke access link

Inputs:
- `user: /core/model/user`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [not-member] The user is not a member: refused.
- [revoked] Otherwise: the member's AccessLink is revoked, as
  /core/operations/revoke-my-access-link/revoked, in every association
  they belong to, also when they have none.

## Migrate slugs

Trigger: once, when slugs were introduced.

Cases:
- [legacy] Each association gets the slug derived from its name,
  followed by `-2`, `-3`… when taken or `new`, the whole cut to keep
  /core/model/association/slug-format.
