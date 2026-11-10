# Model

## User

A person known to the system. Their account is what the system holds
about them.

- `id: UUID`
- `display_name: string`, may be a pseudonym.
  - [display-name] Not empty.
- `email: string`, null once the account is deleted.
  - [email] Unique, compared ignoring case.
- `password: string`, optional: what the user signs in with, along with
  their email.
- `email_verified_at: timestamp`, null until the email is confirmed.
- `deleted_at: timestamp`, null until the user deletes their account.
- `superuser: boolean`, not stored.
  - [superuser] True when `email` equals the `SUPERUSER_EMAIL`
    environment variable, ignoring case; always false when that
    variable is unset.

## EmailVerificationToken

A pending confirmation of a user's email.

- `token: string`, random.
  - [token] Unique.
- `user: /core/model/user`
- `expires_at: timestamp`
  - [expiry] 24 hours after creation.
- [single] At most one per user.

## PasswordResetToken

A pending password reset for a user.

- `token: string`, random.
  - [token] Unique.
- `user: /core/model/user`
- `expires_at: timestamp`
  - [expiry] 1 hour after creation.
- [single] At most one per user.

## AccessLink

A user's lasting sign-in link.

- `token: string`, random.
  - [token] Unique.
- `user: /core/model/user`
- [single] At most one per user.
- [lasting] It does not expire (not testable).

## Association

A legal entity or an informal collective.

- `id: UUID`
- `name: string`
  - [name] Not empty.
- `slug: string`, identifies the association in its screens' URLs.
  - [slug-format] 1 to 50 lowercase letters, digits and hyphens,
    starting and ending with a letter or a digit.
  - [slug-unique] Unique among associations, and never `new`.
  - [derived] The slug derived from a name is the name in lowercase,
    without accents, each run of other characters becoming one hyphen,
    without a leading or trailing hyphen, cut to 50 characters.
  - [legacy] An association created before slugs existed got the slug
    derived from its name, followed by `-2`, `-3`… when taken.
- `timezone: string`, an IANA timezone name.
  - [timezone] Always `Europe/Paris`.

## Membership

A user in an association.

- `user: /core/model/user`
- `association: /core/model/association`
- `role: string`, `manager` or `volunteer`.
- [single] At most one per user and association.
- [manager] An association with at least one member has at least one
  manager.
