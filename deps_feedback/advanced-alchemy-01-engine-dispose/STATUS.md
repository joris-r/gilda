# Status

- **Upstream:** not reported yet.
- **In the project:** the backend tests build the application once per
  pytest-xdist worker (the session fixture `server` in
  `backend/tests/conftest.py`), and any other app a test builds never
  runs its lifespan.
- **Backlog:** none.
- **Done when:** Advanced Alchemy fixes it. Nothing in the project then
  changes, as the one app per worker is kept for speed; this folder can
  go.
