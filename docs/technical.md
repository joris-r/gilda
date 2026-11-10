# Technical

- Repository layout:
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
- Backend:
  - Python 3.13, managed with uv.
  - Litestar, with Advanced Alchemy repositories for data access.
  - PostgreSQL, through SQLAlchemy async with asyncpg; schema changes
    through Advanced Alchemy's Alembic migrations.
  - Configuration from environment variables; the database from
    `DATABASE_URL`, the superuser from `SUPERUSER_EMAIL`; sign-up is
    open unless `INVITATION_ONLY` is `true`.
  - Setting a preference is a single PostgreSQL
    `INSERT … ON CONFLICT (user_id, slot_id) DO UPDATE`; the last write
    wins.
- Web interface:
  - Rendered by Litestar with Jinja, made interactive with Datastar
    through `datastar-py`. The Datastar script is a static file of the
    repository; no npm and no build step.
  - Each URL answers a full page. Each action answers a short-lived SSE
    response that patches the page or leads to another URL; no
    connection stays open. The URLs of the actions are left to the
    implementation.
  - The interface's language comes from the `language` cookie, set by
    the language selector, then from the `Accept-Language` header.
  - Translations live in one file per language; English is the
    reference, every key has a French translation.
  - The header logo is `web/static/favicon.svg`, shown as an image; in
    dark mode, its dot takes the dark accent colour.
- Every entity is identified by a UUIDv7.
- Passwords are stored hashed with Argon2, never in clear.
- Sessions are server-side, stored in PostgreSQL; the browser keeps
  only a session identifier, in an `HttpOnly` cookie.
- Email is sent:
  - Production: handed to the server's local `sendmail` binary.
  - Development and tests: Mailpit, run alongside PostgreSQL in
    `compose.yaml`, on non-default ports; backend and end-to-end tests query it over
    HTTP to read the sent email.
  - The two are selected by whether `SMTP_HOST` is set: set, SMTP;
    unset, `sendmail`.
  - Email texts live in the backend, next to the code that sends
    them, in English and French.
- Deployment: one hosted site, served by Litestar.
- Local development: `compose.yaml` runs Mailpit and two PostgreSQL
  servers: the development one, whose data lives in a named volume, and
  the tests' one, whose data lives in memory.
- Test and quality policy:
  - Backend and end-to-end tests never touch the development database.
  - Backend: pytest, through Litestar's test client, against a real
    PostgreSQL given by `DATABASE_URL`; never SQLite or a mocked
    database.
    - Tests run in parallel with pytest-xdist, one worker per CPU; each
      test sees only the data it creates.
    - Tests hash passwords with Argon2 at its minimal cost parameters.
  - Screens: pytest, through Litestar's test client, on the HTML and
    the SSE responses, for what the server decides (content, what each
    role sees, messages); Playwright for what only happens in the
    browser (e.g. Escape closing a dialog).
  - End-to-end: Playwright against the running backend and database,
    one test per scenario of `scenarios.md`. Tests check text and
    behavior, never screenshots or appearance.
  - Quality: ruff (lint and format) and mypy in strict mode for the
    backend.
  - Every run of each suite (pytest, Playwright) reports its total
    duration and its ten slowest tests.
  - All tests and quality checks pass before every hand-over.
