# Dev43

This project follows the Dev43 process. Before any work, load the
`dev43:core` skill and follow it.


# Project 

Run tests and quality checks only through the Makefile targets
(`make test-backend`, `make lint`…): they set the environment and start
the containers.

Save the full output of every test or quality run to a file, then filter
that file; never pipe a run through a filter. Use `grep -a` on that
file: its non-text bytes can make a plain `grep` find nothing.

To pass options to pytest, set `PYTEST_ADDOPTS` on the Makefile
target: `PYTEST_ADDOPTS="-n0 tests/core" make test-backend`.
To pass options to Playwright, set `E2E_ARGS`:
`make test-e2e E2E_ARGS="tests/members.spec.ts"`.

In a worktree other than the main one, run `make` with
`COMPOSE_PROJECT_NAME=gilda`, or Compose starts a second set of
containers on the same ports.

A test of a newly served page asserts its status, as the Not found page
shares its header.

A test looks for a text within the section or dialog it means, or for
its visible copy: in pytest through the readers of `tests/page.py`,
which keep only what is shown; in Playwright with
`.filter({ visible: true })`. The header's closed dialogs hold hidden
copies of the generic error.

A test asserting only an absence also asserts something present.

Tests read from the database only what no screen shows (ids, rows
already erased).

When a change alters what a screen shows, search the tests also by the
visible text (in English and in French) and by the helpers that build
it, not only by the paths they cite: a test may check the text without
citing the path.

`deps_feedback/` holds the issues found in the project's dependencies,
one folder per issue, named `<dependency>-<nn>-<subject>`. Take them
into account. Each folder's `STATUS.md` says whether the issue is
reported, what in the project works around it, the backlog entry
waiting on it, and when it is done: read it first, and update it when
any of these changes.
