# Data model

- User
  - id: UUID
  - display_name: free text, not empty; may be a pseudonym
  - email: unique, compared ignoring case
  - password: optional; a user with a password has an account, a user
    without one is only a member of associations
  - email_verified_at: timestamp, null until the email is confirmed; a
    user can only sign in once it is set
- EmailVerificationToken: a pending confirmation for a user
  - token: random, unique
  - user_id
  - expires_at: 24 hours after creation
  - R8: Creating a new token for a user deletes that user's previous
    one.
- Association
  - id: UUID
  - name: free text, not empty
- Membership: a user in an association, at most one per pair
  - role: `manager` or `volunteer`
  - R1: An association always has at least one manager.
