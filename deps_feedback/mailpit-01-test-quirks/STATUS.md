# Status

- **Upstream:** not reported yet.
- **In the project:**
  - `MP_MAX_MESSAGES: "0"` in `compose.yaml`, and Mailpit emptied at the
    start of each backend run (`backend/tests/conftest.py`);
  - the latest email chosen by `Created` in
    `backend/tests/core/conftest.py` and `e2e/tests/helpers.ts`;
  - `time.sleep(0.01)` between two emails to one address in three
    backend test files.
- **Backlog:** Tooling: pin the Mailpit image.
- **Done when:** this stays as long as the tests use Mailpit. The image
  is not pinned, so check this folder when a Mailpit change breaks an
  email helper.
