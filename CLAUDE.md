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

When a change alters what an element shows, the Tests phase also looks
for test lookups that match that text over the whole page (e.g.
`"Alice" in response.text`, or `page.getByText('Alice')`), not only for
the tests citing the rule.

A test of a newly served page asserts its status, as the Not found page
shares its header.

On a signed-in screen, a test looks for the generic error within `main`
or its dialog, as the header's closed dialogs hold hidden copies of it.

When a test copies an expectation from another spec, the Tests phase
checks that the fixtures it relies on match (e.g. a planning period
that changes the default range, or a client that holds a `language`
cookie).
