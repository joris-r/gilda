# Mailpit as the test mail catcher: three quirks

Mailpit catches the emails the application sends in development and
tests. The backend tests (pytest) and the end-to-end tests (Playwright)
read them through its HTTP API, to get a confirmation, reset or access
link. Three of its behaviors cost the project time.

## Versions

- `docker.io/axllent/mailpit:latest`, not pinned (see `compose.yaml`).
  The ID change below came with v1.31.

## 1. Pruning stalls reads

By default Mailpit keeps at most 500 messages and prunes the oldest in
bulk. Once the backend suite ran in parallel (8 pytest-xdist workers),
a prune stalled the API's reads for up to 7.7 s, past the 5 s the email
helpers wait, and tests failed at random.

- **What we do:** `MP_MAX_MESSAGES: "0"` in `compose.yaml` turns the cap
  off, and each backend run empties Mailpit first
  (`backend/tests/conftest.py`). Development emails are lost at each
  run; the human accepted it.

## 2. IDs are not in time order, and `Created` has millisecond precision

To find the latest email sent to an address, the helpers cannot sort
by message ID. They take the message with the latest `Created`. Two
emails sent to the same address within the same millisecond cannot be
told apart that way.

- **What we do:** `latest_email` in `backend/tests/core/conftest.py` and
  the token reader in `e2e/tests/helpers.ts` pick the latest
  `Created`. Tests that send two emails to one address and need the
  second wait 10 ms between them (`time.sleep(0.01)` in three test
  files).

## 3. The ID format changed

The helpers once relied on message IDs being ULIDs, which sort by
time. Mailpit v1.31 stopped using ULIDs and a test broke. As the image
is not pinned, the change arrived without an upgrade of ours.

- **What we do:** quirk 2's workaround replaced the ULID ordering.

## What upstream could do

Not checked against Mailpit's current documentation or issues.

- Prune in small steps, or in the background, so reads do not stall.
- Give each message a strictly ordered field (a sequence number, or a
  `Created` with sub-millisecond precision), or document the sort order
  of search results.
- Announce ID format changes as breaking in the release notes.
