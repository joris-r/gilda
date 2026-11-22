# Test quality

The test suite gets faster, sturdier and measured. No increment
integrates a section of `docs/`: each lists the work it does, and adds
to the test policy of `technical.md` the rule it finds worth keeping.

## Outline

1. Speed done
2. Sturdy page reading done
3. Flakiness and time done
4. Weak and missing tests done
5. Tooling done
6. Clock, `code-only`: a clock injected into the services.
7. Past states, `tests-only`: the tests reach past states through the clock instead of SQL.

## Lessons

### Flakiness and time (flaky-tests-and-waits)

- Serves 6 and 7: the backend's checks that no email was sent rely on email being sent within the request, with no sleep; if sending becomes asynchronous, those checks become vacuous.

### Weak and missing tests (weak-and-missing-tests)

- Serves 6 and 7: the World of `test_general_rules.py` and the test of a registration today take their dates from `date.today()` (host UTC) or time_machine; once a clock is injected, they follow it.
- Serves 7: the backend suite ran 150–158 s against its 3 min budget (the general-rules table costs about 20 s); a test reaching a past state through the clock must not build more than it replaces.

### Tooling (test-tooling)

- Serves 7: run `make test-e2e E2E_ARGS=<spec>` on the specs a change touches first, then the full run.

### Mutation testing of `planning/services.py` (mutation-probe)

What was done: a one-off run on 60 of the 230 possible mutants of `planning/services.py` (random sample; comparison flips, `and`/`or`, `not` removal, `+`/`-`, boolean and integer constants, return values replaced by `None`, negated `if` conditions). Each mutant was applied to a scratch copy, and the 722 planning tests were run with `-x`. 55 mutants were killed (92%), 5 survived, none timed out.

- Serves any later mutation run: mutmut has no pytest-xdist support, so with `-n auto` its stats phase sees no covered code. Without xdist, the `RecursionError` in Advanced Alchemy's `_ensure_unique` is gone since backend-test-speed (one app per worker), so retry mutmut without xdist. Otherwise use a throwaway harness: one mutant at a time, xdist, `-x`. A killed mutant costs 10 s to 3 min, a surviving one a full planning run (about 4 min, less since backend-test-speed).
- Serves any later standing mutation check: not worth it for now. The planning tests are strong and a run is slow; revisit after the `new_client` fixture is fixed.

### Coverage of the backend tests (coverage-probe)

What was done: a one-off measure of line and branch coverage of `backend/src/gilda` by the whole backend suite (1,214 tests, xdist), in a scratch copy; nothing was added to the project. Result: 97% (52 of 2,505 statements and 30 of 418 branches missed). Templates, JavaScript and the end-to-end suite are not measured.

- Serves any later coverage check, a standing one included: with coverage.py's defaults the result is 67%, a wrong figure, as SQLAlchemy's async code runs in greenlets and the lines after an `await` are lost (the line after `await self._manager_of(...)` read as missed). The `.coveragerc` needs `concurrency = greenlet,thread` and `branch = true`; `pytest-cov` runs with xdist.
- Coverage does not replace the mutation run: the mutants that survived (`end_membership`, `_default_range`) sit on covered lines, as the tests run the code without asserting the boundary.

## For the human

- Return e2e to TypeScript 7 once typescript-eslint supports it.
- End-to-end: type-aware ESLint (`no-floating-promises`) to catch a missing await on a Playwright action.
- Remove `_one_line()` from `planning/pages.py`, now that `shown()` rebuilds patches (`code-only`).
- Tests read action responses through `patched()` and the page readers, not raw `in shown()` / `unescape(page)` text (`tests-only`).
- Forms submit natively (GET) if submitted before Datastar starts; a slow network lets a user hit it.
- Defensive guards no specified path reaches (core/planning/home re-checks, 'Give a name or a slug.', 'Give both from and to, or neither.', preference refusals, registration back to proposed, take-over error without the flag): keep or remove as dead code.
