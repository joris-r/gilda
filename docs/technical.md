# Technical

## Repository layout

- `backend/`: the web interface.
- `e2e/`: the end-to-end tests.
- Backend layout, under `backend/src/gilda/`:
  - One folder per domain (e.g. `core/`), each with its own files,
    present only when needed:
    - `pages.py`: the Litestar handlers of the screens.
    - `templates/`: the Jinja templates of the screens.
    - `models.py`: the SQLAlchemy models.
    - `repositories.py`: the Advanced Alchemy repositories.
    - `schemas.py`: the request and response types.
    - `services.py`: the logic between handlers and repositories.
  - `home/`: serves My associations, gathering what each domain shows
    of an association there.
  - `db.py`: the database configuration.
  - `web/`: what the screens share: the page layout, the translations,
    the language selection and the static files.
  - `app.py`: only assembles the application from the domains and the
    configuration.
  - Tests in `backend/tests/`, one folder per domain.

## Backend

- Python 3.13, managed with uv.
- Litestar, with Advanced Alchemy repositories for data access.
- PostgreSQL, through SQLAlchemy async with asyncpg; schema changes
  through Advanced Alchemy's Alembic migrations.
- Configuration from environment variables; the database from
  `DATABASE_URL`, the superuser from `SUPERUSER_EMAIL`; sign-up is
  open unless `INVITATION_ONLY` is `true`.
- The backend's code reads the current time only from one clock, given
  to the application when it is built; its dependencies keep their own,
  and so does the expiry of the stored sessions.
- Setting a preference is a single PostgreSQL
  `INSERT … ON CONFLICT (user_id, slot_id) DO UPDATE`; the last write
  wins.

## Web interface

- Rendered by Litestar with Jinja, made interactive with Datastar
  through `datastar-py`. The Datastar script is a static file of the
  repository; no npm and no build step.
- Each URL answers a full page. Each action answers a short-lived SSE
  response that patches the page or leads to another URL; no
  connection stays open. The URLs of the actions are left to the
  implementation.
- A read-only URL may answer a bare HTML fragment with plain status
  codes, where a refresh must fail silently.
- Once Datastar has started, the layout sets `data-ready` on the body,
  by a `data-init`.
- The interface's language comes from the `language` cookie, set by
  the language selector, then from the `Accept-Language` header.
- Translations live in one file per language; English is the
  reference, every key has a French translation.
- The header logo is `web/static/favicon.svg`, shown as an image; in
  dark mode, its dot takes the dark accent colour.

## Identifiers and security

- Every entity is identified by a UUIDv7.
- Passwords are stored hashed with Argon2, never in clear.
- Sessions are server-side, stored in PostgreSQL; the browser keeps
  only a session identifier, in an `HttpOnly` cookie.
  - A response stores its session, and sets the cookie, only when its
    request changed the session.
  - The `session` cookie lasts a year; a stored session expires once
    unused for 14 days.

## Email

- Production: handed to the server's local `sendmail` binary.
- Development and tests: Mailpit, run alongside PostgreSQL in
  `compose.yaml`, on non-default ports; backend and end-to-end tests
  query it over HTTP to read the sent email.
- The two are selected by whether `SMTP_HOST` is set: set, SMTP;
  unset, `sendmail`.
- Email texts live in the backend, next to the code that sends them,
  in English and French.

## Deployment and local development

- Deployment: one hosted site, served by Litestar.
- Local development: `compose.yaml` runs Mailpit and two PostgreSQL
  servers: the development one, whose data lives in a named volume, and
  the tests' one, whose data lives in memory.

## Test and quality policy

- Backend and end-to-end tests never touch the development database.
- Tests wait on a condition, never for a fixed time, except to check
  that nothing happens where nothing shows that it will not.
- Every run of each suite (pytest, Playwright) reports its total
  duration and its ten slowest tests.
- All tests and quality checks pass before every hand-over.

### Backend tests

- pytest, through Litestar's test client, against a real PostgreSQL
  given by `DATABASE_URL`; never SQLite or a mocked database.
- Tests run in parallel with pytest-xdist, one worker per CPU; each
  test sees only the data it creates.
- Tests hash passwords with Argon2 at its minimal cost parameters.
- Each worker builds the application once; every test client of the
  worker, one per browser, runs on it.
- The whole suite runs in at most 3 min on 8 cores, and a run
  reports no warning.
- The page readers of the tests read a page as the browser shows it:
  through an HTML parser, only its visible elements, their text
  unescaped; an SSE patch as the HTML its `data: elements` lines
  rebuild. They find a dialog by its name, never by its position on
  the page.
- Each statement of a `## General` section of the operations is
  checked by one test over a table of the actions of the screens; a
  route of the application that is neither in the table nor a page
  fails it.
- A test moves time only through the application's clock, never
  through the system's time or by rewriting a stored time or date.
- Mailpit keeps every email it catches; each backend run empties it
  before its tests start.

### End-to-end tests

- An action waits at most 5 s for its element. After each load of a
  page (goto, reload, a link followed, an action leading to another
  URL), a test waits for the page's `data-ready` before acting on it.
- Each run starts its own server; it fails if its port is already
  taken.

### Test levels

- Backend: pytest, through Litestar's test client, against a real
  PostgreSQL. It observes what the server decides: the status, the
  HTML and SSE responses (content, what each role sees, messages), the
  database, the sent emails read from Mailpit. It cannot observe what
  happens in the browser.
- End-to-end: Playwright against the running backend and database,
  one test per scenario of `scenarios.md`, plus the behaviors only a
  browser shows (e.g. Escape closing a dialog, focus, navigation, a
  Datastar patch applied to the page). It checks text and behavior,
  never screenshots or appearance, and does not repeat what a backend
  test establishes.

### Quality

- ruff (lint and format) and mypy in strict mode for the backend; a
  check that every Datastar action in the templates sets
  `retryMaxCount: 0`.
- Prettier, ESLint and tsc for the end-to-end tests.
