# Data model

- User
  - id: UUID
  - display_name: free text, not empty; may be a pseudonym
  - email: unique, compared ignoring case
  - password: optional; a user with a password has an account and can
    sign in, a user without one is only a member of associations
- Association
  - id: UUID
  - name: free text, not empty
- Membership: a user in an association, at most one per pair
  - role: `manager` or `volunteer`
  - R1: An association always has at least one manager.
