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

In a worktree other than the main one, run `make` with
`COMPOSE_PROJECT_NAME=gilda`, or Compose starts a second set of
containers on the same ports.

A test of a newly served page asserts its status, as the Not found page
shares its header.

On a signed-in screen, a test looks for the generic error within `main`
or its dialog, as the header's closed dialogs hold hidden copies of it.

When a change alters what a screen shows, search the tests also by the
visible text (in English and in French) and by the helpers that build
it, not only by the paths they cite: a test may check the text without
citing the path.
