# Test quality

The test suite gets faster, sturdier and measured. No increment
integrates a section of `docs/`: each lists the work it does, and adds
to the test policy of `technical.md` the rule it finds worth keeping.

## Outline

1. Measure:
   - A one-off mutation-testing run on one domain (e.g. `planning/services.py`), with a tool outside the project's dependencies, to learn whether the tests fail when the code is wrong; then decide whether it becomes a standing check.
2. Speed:
   - Profile and cut the fixed cost per backend test: 1202 tests take 5 min 05 s on 8 cores, about 2 s of CPU each, the ten slowest about 5 s; then decide a time budget for the suite.
   - Remove the 172,221 warnings of a backend run, all Litestar's deprecation of path parameters declared by inference.
   - Backend tests: report to Advanced Alchemy that its Litestar lifespan disposes only the first config's engine per process, then drop the workaround in the new_client fixture.
3. Sturdy page reading:
   - Tests: the regex page helpers (`lines_of`, `line_of`, `section_of`…) would use an HTML parser, as `listed` does, read only the visible elements and unescape the text, so that nested lists, hidden copies and headings with an apostrophe read right.
   - Tests: `shown()` would rebuild the HTML of each `datastar-patch-elements` event from its `data: elements` lines, so pytest reads a patch as the browser does and templates need not be sent on one line.
   - Tests: the pytest tests that find a dialog by its position on the page would find it by its name.
   - End-to-end: a helper would look up a display name on the Schedule within the menu (`#occurrence-menu`), since occurrences are buttons named after their registrations.
   - Process: CLAUDE.md would gain three test rules: a test looks for text within the section or dialog it means, or for its visible copy (replacing the rule on the generic error's hidden copies); a test asserting only an absence also asserts something present; tests read from the database only what no screen shows (ids, rows already erased).
   - Process: CLAUDE.md's rule on the generic error in `main` would say to filter visible elements in Playwright (`.filter({ visible: true })`), as the header's dialogs hold hidden copies (a return to Tests in polish-changed-identifier).
4. Flakiness and time:
   - End-to-end: investigate the intermittent failure of one test per run (scenarios, notices); for notices, see the one-shot POST entry.
   - Tests: a clock injected into the services, so tests reach past states without SQL.
   - End-to-end: a shorter `actionTimeout`, so a suite failing on a missing screen ends fast.
   - Tests: replace the fixed waits (10 `waitForTimeout` in the end-to-end tests, the 0.5 s sleeps of the backend tests) by waits on a condition, where one exists.
5. Weak and missing tests:
   - Tests: strengthen weak existing tests found by the migration: the e2e share-link revoke test never asserts "None", the only-member account deletion asserts only status 200, and the Schedule's date order is checked only through the column layout.
   - Quality: harden the e2e tests of Access link and Confirm email: Try again hidden while the action runs and the running text back after it; Try again failing again on Confirm email; a failure by network abort, not only a 500; and `getByText('My associations')` scoped in the Confirm email test.
   - Tests: stale-screen e2e tests (changed identifier in another tab) for Members role/remove/send-link/revoke-link, the period, closure and share-link dialogs, absence edit/delete, propose and cancel; they share the X-Association mechanism.
   - Tests: the general rules checked once per action (signed out, a missing or invalid field) as one parametrized test per rule over a table of actions, compared with the application's routes so a new action cannot miss its row.
6. Tooling:
   - End-to-end: `make test-e2e` would take arguments (e.g. a spec file or a grep) to run one spec.
   - Tooling: e2e should not reuse a server already running on its port, or `make test-e2e` should check the port first.
   - End-to-end: `tsc --noEmit` reports three type errors in errors-once.spec.ts (Promise<string[]> not assignable to Promise<void>).
   - Quality: run Prettier and ESLint on `e2e/` in `make lint`, with a Prettier config matching the project's style (single quotes, no semicolons); `scenarios.spec.ts` is not formatted today, and `members.spec.ts` was formatted with Prettier's defaults.

## Lessons
