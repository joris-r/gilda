# Test quality

The test suite gets faster, sturdier and measured. No increment
integrates a section of `docs/`: each lists the work it does, and adds
to the test policy of `technical.md` the rule it finds worth keeping.

## Outline

1. Speed done
2. Sturdy page reading done
3. Flakiness and time done
4. Weak and missing tests, `tests-only`:
   - Tests: strengthen weak existing tests found by the migration: the e2e share-link revoke test never asserts "None", the only-member account deletion asserts only status 200, and the Schedule's date order is checked only through the column layout.
   - Quality: harden the e2e tests of Access link and Confirm email: Try again hidden while the action runs and the running text back after it; Try again failing again on Confirm email; a failure by network abort, not only a 500; and `getByText('My associations')` scoped in the Confirm email test.
   - Tests: stale-screen e2e tests (changed identifier in another tab) for Members role/remove/send-link/revoke-link, the period, closure and share-link dialogs, absence edit/delete, propose and cancel; they share the X-Association mechanism.
   - Tests: the general rules checked once per action (signed out, a missing or invalid field) as one parametrized test per rule over a table of actions, compared with the application's routes so a new action cannot miss its row.
5. Tooling, `direct`:
   - End-to-end: `make test-e2e` would take arguments (e.g. a spec file or a grep) to run one spec.
   - Tooling: e2e should not reuse a server already running on its port, or `make test-e2e` should check the port first.
   - End-to-end: `tsc --noEmit` reports three type errors in errors-once.spec.ts (Promise<string[]> not assignable to Promise<void>).
   - Quality: run Prettier and ESLint on `e2e/` in `make lint`, with a Prettier config matching the project's style (single quotes, no semicolons); `scenarios.spec.ts` is not formatted today, and `members.spec.ts` was formatted with Prettier's defaults.
6. Clock, `code-only`: a clock injected into the services.
7. Past states, `tests-only`: the tests reach past states through the clock instead of SQL.

## Lessons

### Sturdy page reading (sturdy-page-reading)

- Serves 3 and 4: pytest reads pages through `backend/tests/page.py`; a new reader goes there, never as a regular expression on tags, and parses `patched(response)`, not `shown()`, which is already unescaped.
- Serves 4: Members shows its first five members until "Show all", and the page readers see only those.
- Serves 4: the delete questions held in `data-question` reach their dialog only in the browser, so the end-to-end tests are where they are seen shown.

### Mutation testing of `planning/services.py` (mutation-probe)

What was done: a one-off run on 60 of the 230 possible mutants of `planning/services.py` (random sample; comparison flips, `and`/`or`, `not` removal, `+`/`-`, boolean and integer constants, return values replaced by `None`, negated `if` conditions). Each mutant was applied to a scratch copy, and the 722 planning tests were run with `-x`. 55 mutants were killed (92%), 5 survived, none timed out.

- Serves any later mutation run: mutmut has no pytest-xdist support, so with `-n auto` its stats phase sees no covered code. Without xdist, the `RecursionError` in Advanced Alchemy's `_ensure_unique` is gone since backend-test-speed (one app per worker), so retry mutmut without xdist. Otherwise use a throwaway harness: one mutant at a time, xdist, `-x`. A killed mutant costs 10 s to 3 min, a surviving one a full planning run (about 4 min, less since backend-test-speed).
- Serves 4, two missing tests found by the survivors:
  - `end_membership`: `Registration.date >= today` became `> today` and no test failed: no test leaves an association with a registration today.
  - `_default_range`: the end of the default Schedule range (`days=-1`) became `-2` and no test failed: the last day of the range is not checked.
- Serves 4, a weak spot: the values returned by `edit_slot` and `edit_closure` are replaced by `None` without a failure, as the tests observe only the screens. Low risk.
- The fifth survivor, `_is_occurrence` returning `None` instead of `False`, is an equivalent mutant: nothing to fix.
- Serves any later standing mutation check: not worth it for now. The planning tests are strong and a run is slow; revisit after the `new_client` fixture is fixed.

### Coverage of the backend tests (coverage-probe)

What was done: a one-off measure of line and branch coverage of `backend/src/gilda` by the whole backend suite (1,214 tests, xdist), in a scratch copy; nothing was added to the project. Result: 97% (52 of 2,505 statements and 30 of 418 branches missed). Templates, JavaScript and the end-to-end suite are not measured.

- Serves any later coverage check, a standing one included: with coverage.py's defaults the result is 67%, a wrong figure, as SQLAlchemy's async code runs in greenlets and the lines after an `await` are lost (the line after `await self._manager_of(...)` read as missed). The `.coveragerc` needs `concurrency = greenlet,thread` and `branch = true`; `pytest-cov` runs with xdist.
- Serves 4, no backend test reaches these, though the end-to-end tests may:
  - the `POST /language` and `GET /notice` routes (`web/pages.py`) and the notice claim of `web/rendering.py`;
  - the preferences route of the Members screen shown again after being hidden (`planning/pages.py`, 401, 404 and 403 answers);
  - the sendmail fallback and the quality parse of the language header (`mailer.py`).
- Serves 4, defensive guards no test reaches, where each would be either tested or removed as dead code: the "Not a member of this association." and "Association not found." re-checks of `core/services.py`, `planning/services.py` and `home/services.py`; "Give a name or a slug."; "Give both from and to, or neither."; the preference's missing slot, member and manager-only refusals; a registration going back to proposed.
- Serves 4, the Schedule layout's reuse of a free lane (`planning/pages.py`) and the choice of the take-over error in the dialog are never reached.
- Coverage does not replace the mutation run: the mutants that survived (`end_membership`, `_default_range`) sit on covered lines, as the tests run the code without asserting the boundary.

## For the human

- Remove `_one_line()` from `planning/pages.py`, now that `shown()` rebuilds patches (`code-only`).
- Tests read action responses through `patched()` and the page readers, not raw `in shown()` / `unescape(page)` text (`tests-only`).
