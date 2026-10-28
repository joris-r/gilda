# health-check: a status page across the whole stack

A web page, in English and French, shows whether the API and the
database are reachable.

## GET /api/health

All API endpoints are under `/api`.

```http
GET /api/health
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"api": "ok", "database": "ok"}
```

When the database is unreachable:

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{"api": "ok", "database": "unreachable"}
```

## Status page

The page at `/` calls `GET /api/health` and shows:

```
Gilda status
API: reachable
Database: reachable
```

When the database is unreachable:

```
Gilda status
API: reachable
Database: unreachable
```

When the API does not answer:

```
Gilda status
API: unreachable
Database: unknown
```

- The interface is in English by default.
- A language selector, on every page, switches between English and
  French; the choice is kept in the browser across visits.

In French:

```
État de Gilda
API : accessible
Base de données : accessible
```

## Technical

- Repository layout:
  - `backend/`: the API.
  - `frontend/`: the web interface.
  - `e2e/`: the end-to-end tests.
- Backend layout, under `backend/src/gilda/`:
  - One folder per domain (e.g. `health/`), each with its own files,
    present only when needed:
    - `controllers.py`: the Litestar controllers.
    - `models.py`: the SQLAlchemy models.
    - `repositories.py`: the Advanced Alchemy repositories.
    - `schemas.py`: the request and response types.
    - `services.py`: the logic between controllers and repositories.
  - `db.py`: the database configuration.
  - `app.py`: only assembles the application from the domains and the
    configuration.
  - Tests in `backend/tests/`, one folder per domain.
- Backend:
  - Python 3.13, managed with uv.
  - Litestar, with Advanced Alchemy repositories for data access.
  - PostgreSQL, through SQLAlchemy async with asyncpg; schema changes
    through Advanced Alchemy's Alembic migrations.
  - Configuration from environment variables; the database from
    `DATABASE_URL`.
- Frontend:
  - Vue 3, TypeScript, Vite, Vue Router, vue-i18n; npm.
  - Talks to the backend only through the JSON API.
  - Translations live in one file per language; English is the
    reference, every key has a French translation.
- Deployment: one alwaysdata site. Litestar serves the API under
  `/api` and the built frontend files for every other path.
- Local development: `compose.yaml` runs PostgreSQL.
- Test and quality policy:
  - Backend: pytest, through Litestar's test client, against a real
    PostgreSQL given by `DATABASE_URL`; never SQLite or a mocked
    database.
  - Frontend: Vitest with Vue Test Utils, the API mocked.
  - End-to-end: Playwright against the running backend, frontend and
    database, for typical user scenarios only. Tests check text and
    behavior, never screenshots or appearance.
  - Quality: ruff (lint and format) and mypy in strict mode for the
    backend; ESLint, Prettier and vue-tsc for the frontend.
  - Every run of each suite (pytest, Vitest, Playwright) reports its
    total duration and its ten slowest tests.
  - All tests and quality checks pass before every hand-over.
