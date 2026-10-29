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

## Deploy

One alwaysdata site serves both the API and the built frontend, from
the same Litestar app. Site, PostgreSQL database and SMTP relay are
configured directly on alwaysdata.

One-time site setup needs:

- A Python app, ASGI entry point `gilda.app:create_app`.
- A PostgreSQL database, and `DATABASE_URL` set to
  `postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>`.
- `GILDA_FRONTEND_DIR` set to the absolute path of `frontend/dist`
  (built below).
- `FRONTEND_URL` set to the site's public URL, including the scheme
  (e.g. `https://your-site.example`; used in confirmation emails).
- `SMTP_FROM` set to the sender address for confirmation emails.
  `SMTP_HOST`/`SMTP_PORT` (currently unauthenticated SMTP over TCP) do
  not work on alwaysdata as-is: there is no local SMTP listener, and
  alwaysdata requires either SMTP AUTH or using the local `sendmail`
  binary directly. Production email sending needs the mailer rework
  on the backlog first.
- SSH access, with this repository cloned on the site.

To deploy, over SSH on the site:

```sh
cd gilda
git pull
cd backend && uv sync --no-dev && cd ..
cd frontend && npm install && npm run build && cd ..
cd backend && uv run litestar --app gilda.app:create_app database upgrade --no-prompt
```

Then restart the site so it picks up the new code.

## Dev43

The development process is Dev43: see `spec/`.
