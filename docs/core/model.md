# Model

## Id

A string identifying an entity.

- [unique] No two entities share one.

## Instant

A date and a time, to the second.

## Configuration

Read from the environment when the software starts.

- `superuser_email: optional string`, `SUPERUSER_EMAIL`; none when it
  is unset.
- `invitation_only: boolean`, whether `INVITATION_ONLY` is `true`.

## User

A person known to the system. Their account is what the system holds
about them.

- `id: /core/model/id`
- `display_name: string`, may be a pseudonym.
  - [display-name] Not empty.
- `email: optional string`, none once the account is deleted.
  - [email] No two users have the same email.
- `password: optional string`, what the user signs in with, along with
  their email; none for a user who never chose one.
- `email_verified_at: optional /core/model/instant`, none until the
  email is confirmed.
- `deleted_at: optional /core/model/instant`, none until the user
  deletes their account.

Two emails are the same when they are equal ignoring case; none is
not an email. The
superuser's email is the configuration's `superuser_email`; there is
none when it is unset.

## EmailVerificationToken

A pending confirmation of a user's email.

- `token: string`, random.
  - [token] Unique.
- `user: /core/model/user`
- `expires_at: /core/model/instant`
- [single] At most one per user.

## PasswordResetToken

A pending password reset for a user.

- `token: string`, random.
  - [token] Unique.
- `user: /core/model/user`
- `expires_at: /core/model/instant`
- [single] At most one per user.

## AccessLink

A user's lasting sign-in link.

- `token: string`, random.
  - [token] Unique.
- `user: /core/model/user`
- [single] At most one per user.
- [lasting] It does not expire (not testable).

## Session

A browser signed in as a user.

- `id: string`, random; the value of the browser's `session` cookie.
  - [id] Unique.
- `user: /core/model/user`
- `access_link: optional /core/model/accesslink`, the link that
  opened it, if any.

The signed-in user of a request is the user of the session whose id
the request's `session` cookie holds; a request without one is signed
out.

## Association

A legal entity or an informal collective.

- `id: /core/model/id`
- `name: string`
  - [name] Not empty.
- `slug: string`, identifies the association in its screens' URLs.
  - [slug-format] 1 to 50 lowercase letters, digits and hyphens,
    starting and ending with a letter or a digit.
  - [slug-unique] Unique among associations, and never `new`.
- `timezone: string`, an IANA timezone name.
  - [timezone] Always `Europe/Paris`.

The slug derived from a name is the name in lowercase, without
accents, each run of other characters becoming one hyphen, without a
leading or trailing hyphen, cut to 50 characters.

## Membership

A user in an association.

- `user: /core/model/user`
- `association: /core/model/association`
- `role: one of manager, volunteer`
- [single] At most one per user and association.
- [manager] An association with at least one member has at least one
  manager.

A manager of an association is a user with a `manager` membership in
it; a member, a user with any membership in it.

## State

Everything the software stores; the other domains add to it.

- `configuration: /core/model/configuration`
- `users: set of /core/model/user`
- `email_verification_tokens: set of /core/model/emailverificationtoken`
- `password_reset_tokens: set of /core/model/passwordresettoken`
- `access_links: set of /core/model/accesslink`
- `sessions: set of /core/model/session`
- `associations: set of /core/model/association`
- `memberships: set of /core/model/membership`
