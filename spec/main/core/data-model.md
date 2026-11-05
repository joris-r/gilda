# Data model: core

## Scope: Accounts

### Entity: User

A person known to the system. Their account is what the system holds
about them.

- Fields
  - id: UUID
  - display_name: free text, not empty; may be a pseudonym
  - email: unique, compared ignoring case; null once the account is
    deleted
  - password: optional; what the user signs in with, along with their
    email
  - email_verified_at: timestamp, null until the email is confirmed (by
    its confirmation link, a password reset or an access link)
  - deleted_at: timestamp, null until the user deletes their account
    (R29)
- Rules
  - A user can only sign in with their password once email_verified_at
    is set.

### Entity: EmailVerificationToken

A pending confirmation for a user.

- Fields
  - token: random, unique
  - user
  - expires_at: 24 hours after creation
- Rules
  - R8: Creating a new token for a user deletes that user's previous
    one.

### Entity: PasswordResetToken

A pending password reset for a user.

- Fields
  - token: random, unique
  - user
  - expires_at: 1 hour after creation
- Rules
  - R8 applies.

### Entity: AccessLink

A user's lasting sign-in link, at most one per user.

- Fields
  - token: random, unique
  - user
- Rules
  - An access link does not expire.
  - R23: Revoking an access link deletes it; the sessions it signed in
    no longer authenticate.

## Scope: Associations

### Entity: Association

A legal entity or an informal collective.

- Fields
  - id: UUID
  - name: free text, not empty
  - slug: identifies the association in its screens' URLs
    - 1 to 50 lowercase letters, digits and hyphens, starting and
      ending with a letter or a digit
    - unique among associations, and never `new`
  - timezone: an IANA timezone name; always `Europe/Paris`
- Rules
  - R37: An association created before slugs existed gets a slug derived
    from its name as R35 says, followed by `-2`, `-3`… when taken.

### Entity: Membership

A user in an association, at most one per pair.

- Fields
  - user
  - association
  - role: `manager` or `volunteer`
- Rules
  - R1: An association with at least one member has at least one manager.
