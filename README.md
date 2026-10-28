# Gilda

A web service for associations to manage their activities. Several
associations share one deployment, each with its own data; each has a
few dozen volunteers. The first feature planned is scheduling
volunteers.

The interface is in English and French.

## Stack

- `backend/`: JSON API in Python (Litestar, Advanced Alchemy,
  PostgreSQL).
- `frontend/`: web interface in Vue 3 and TypeScript.
- `e2e/`: end-to-end tests with Playwright.

## Run

Everything goes through `make`; `make help` lists the targets.

```sh
make install      # dependencies of every part
make dev          # PostgreSQL, migrations, then backend and frontend with reload
```

The frontend dev server proxies `/api` to the backend on port 8000.
`DATABASE_URL` defaults to the local PostgreSQL of `compose.yaml`.

## Test

```sh
make test         # backend, frontend and end-to-end suites
make lint         # quality checks, changing nothing
make format       # fix lint and formatting
make check        # lint and test: run before every hand-over
```

The development process is Dev43: see `spec/`.
