# Dev43

This project follows the Dev43 process. Before any work, load the
`dev43:core` skill and follow it.

Under `Cases:`, a bulleted list is Dev43's: exactly one case applies to
each state and input. A numbered list is ordered: the first case whose
condition holds applies. The statements of `## General` apply before
the cases of any operation. `Then:`, after the cases, introduces the
statements that hold once a case applied, each saying after which.


# Project 

Run tests and quality checks only through the Makefile targets
(`make test-backend`, `make lint`…): they set the environment and start
the containers.

Save the full output of every test or quality run to a file, then filter
that file; never pipe a run through a filter. Use `grep -a` on that
file: its non-text bytes can make a plain `grep` find nothing.

A test of a newly served page asserts its status, as the Not found page
shares its header.

On a signed-in screen, a test looks for the generic error within `main`
or its dialog, as the header's closed dialogs hold hidden copies of it.
