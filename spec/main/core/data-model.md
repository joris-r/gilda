# Data model

- User
  - id: UUID
  - display_name: free text, not empty; may be a pseudonym
  - email: unique, compared ignoring case; null once the account is
    deleted
  - password: optional; a user with a password has an account, a user
    without one is only a member of associations
  - email_verified_at: timestamp, null until the email is confirmed (by
    its confirmation link, a password reset or an access link); a user
    can only sign in with their password once it is set
  - deleted_at: timestamp, null until the user deletes their account
    (R29)
- EmailVerificationToken: a pending confirmation for a user
  - token: random, unique
  - user_id
  - expires_at: 24 hours after creation
  - R8: Creating a new token for a user deletes that user's previous
    one.
- PasswordResetToken: a pending password reset for a user, as
  EmailVerificationToken (R8 applies)
  - token: random, unique
  - user_id
  - expires_at: 1 hour after creation
- AccessLink: a user's lasting sign-in link, at most one per user
  - token: random, unique
  - user_id
  - It does not expire.
  - R23: Revoking it deletes it; the sessions it signed in no longer
    authenticate.
- Association
  - id: UUID
  - name: free text, not empty
  - slug: identifies the association in its screens' URLs
    - 1 to 50 lowercase letters, digits and hyphens, starting and
      ending with a letter or a digit
    - unique among associations, and never `new`
    - R37: An association created before slugs existed gets one derived
      from its name as R35 says, followed by `-2`, `-3`… when taken.
  - timezone: an IANA timezone name; always `Europe/Paris`
  - The dates and times of its slots, closures, planning period and
    registrations are in this timezone.
- Membership: a user in an association, at most one per pair
  - role: `manager` or `volunteer`
  - R1: An association always has at least one manager.
