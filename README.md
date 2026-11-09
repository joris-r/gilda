# Gilda

A web service for associations to manage their activities. Several
associations share one deployment, each with its own data; each has a
few dozen volunteers. The first feature planned is scheduling
volunteers.

The interface is in English and French.

## Stack

- `backend/`: web interface in Python (Litestar, Advanced Alchemy,
  PostgreSQL, Jinja, Datastar).
- `e2e/`: end-to-end tests with Playwright.

## Run

Everything goes through `make`; `make help` lists the targets.

```sh
make install      # dependencies of every part
make dev          # PostgreSQL, migrations, then the backend with reload
```

The site runs on port 8000.
`DATABASE_URL` defaults to the local PostgreSQL of `compose.yaml`.

## Development environment

`make dev` runs the site and starts the services of `compose.yaml`:

- The site: http://localhost:8000
- Mailpit, which catches every email sent in development and tests:
  http://localhost:18025 (SMTP on port 11025)
- PostgreSQL: `localhost:5432` for development, `localhost:15432` for
  the tests (user and password `gilda`)

## Test

```sh
make test         # backend and end-to-end suites
make lint         # quality checks, changing nothing
make format       # fix lint and formatting
make check        # lint and test: run before every hand-over
```

The backend and end-to-end suites use their own PostgreSQL of `compose.yaml`,
never the development database; `TEST_DATABASE_URL` overrides it.

## Deploy

One hosted site serves the whole web interface, static files included,
from one Litestar app run by uvicorn. It needs Python 3.13, `uv`, SSH
access, a PostgreSQL database, and this repository cloned on the site.

### Environment variables

Set them in the site's settings at the hosting provider:

```sh
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>
FRONTEND_URL=https://your-site.example   # the public URL, used in the emails' links
SMTP_FROM=no-reply@your-site.example     # the sender of the emails
INVITATION_ONLY=true                     # optional: only invited members sign up
SUPERUSER_EMAIL=you@example.org          # optional: may sign up even when invitation-only
```

- Mail: with `SMTP_HOST` unset, the app hands emails to the server's
  `/usr/sbin/sendmail`. Otherwise it sends them to `SMTP_HOST` on
  `SMTP_PORT` (default 25), without authentication.
- `INVITATION_ONLY=true` lets only the people a manager added as
  members create an account, plus `SUPERUSER_EMAIL`, who creates the
  first account and the first association.

### Launch command

Run from `backend/`:

```sh
uv run --no-dev uvicorn --factory gilda.app:create_app --host <host> --port <port> \
  --proxy-headers --forwarded-allow-ips "<address of the provider's proxy>"
```

- `--factory`: `create_app` builds the app.
- `--no-dev`: otherwise `uv run` installs the development tools again.
- `--proxy-headers`: the site sees the visitors' scheme and address
  through the provider's proxy.

uvicorn, run this way, has no hot restart: if the provider asks for a
hot-restart command, leave it empty, so that a restart stops the
process and starts it again.

### Deploy a new version

Over SSH, the variables of the site's settings are not set: export
`DATABASE_URL` first, so that the migrations reach the database.

```sh
export DATABASE_URL='postgresql+asyncpg://…'

cd gilda/backend
git pull
uv sync --no-dev
uv run --no-dev litestar --app gilda.app:create_app database upgrade --no-prompt
```

Then restart the site so it picks up the new code. The first
deployment follows the same steps, before the first start.

## Dev43

The development process is Dev43: see `spec/`.
