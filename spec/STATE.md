# Dev43 state

Updated on the human's decisions, and at the agent's hand-over (Step).

- Dev43: 2.0.0
- Specification: complete
- Increment: session-rotation
- Shape: full
- Phase: Tests
- Step: Production
- Stash:

## Scope of the current increment

- Sign-in (`POST /api/session`) issues a new session ID; the one the
  request came with no longer authenticates.
