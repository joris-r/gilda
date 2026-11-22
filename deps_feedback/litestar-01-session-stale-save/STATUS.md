# Status

- **Upstream:** not reported yet. It has a security impact: report it
  privately, through a GitHub security advisory, to Litestar and to
  Advanced Alchemy.
- **In the project:**
  - the `SessionBackend` subclass in `backend/src/gilda/core/sessions.py`,
    which saves only a changed session and never recreates a deleted one;
  - the session deletes in `backend/src/gilda/core/repositories.py`,
    committed on a connection of their own.
- **Backlog:** Sessions: drop the `SessionBackend` subclass.
- **Done when:** Litestar saves only changed sessions, never recreates a
  deleted one, and can renew the session ID. The subclass and this
  folder can then go.
