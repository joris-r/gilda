# Dev43 state

Updated on the human's decisions, and at the agent's hand-over (Step).

- Dev43: 2.0.0
- Specification: complete
- Increment: email-reliability
- Shape: full
- Phase: Integration
- Step: Exploration
- Stash:

## Scope of the current increment

- Sign-up fails cleanly, not with a raw 500, when the confirmation
  email cannot be sent.
- test_r8 (resend invalidates the previous token) passes.
- The email-verification migration passes ruff check and format.
