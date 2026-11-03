# Dev43

This project follows the Dev43 process. Before any work, load the
`dev43:core` skill and follow it.


# Project 

Run tests and quality checks only through the Makefile targets
(`make test-backend`, `make lint`…): they set the environment and start
the containers.

When a change alters what an element shows, the Tests phase also looks
for test lookups that match that text over the whole page (e.g.
`control(wrapper, 'Alice')`), not only for the tests citing the rule.
