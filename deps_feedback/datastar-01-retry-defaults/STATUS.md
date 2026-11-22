# Status

- **Upstream:** not reported yet. Datastar 1.0.5 fixed `retry: "never"`
  (#1234); the rest of the note still applies to it.
- **In the project:**
  - `retryMaxCount: 0` on every Datastar action of the templates, each
    with a "No retry" comment;
  - `backend/scripts/check_datastar_once.py`, run by `make lint`, which
    fails on an action without it;
  - `e2e/tests/errors-once.spec.ts`, and the helpers of
    `e2e/tests/helpers.ts` that wait for an action's end.
- **Backlog:** Dependencies: upgrade the bundled Datastar from 1.0.4 to
  1.0.5.
- **Done when:** Datastar stops resending one-shot actions by default,
  or lets an application set the retry options once for every action.
  The per-action option and its lint check can then go; the tests stay,
  as they check `/ui/errors/once`.
