# Deploy Gilda

One hosted site serves the whole web interface, static files included,
from one Litestar app run by uvicorn. It needs Python 3.13, `uv`, SSH
access, a PostgreSQL database, and this repository cloned on the site.

## Environment variables

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

## Launch command

Run from `backend/`:

```sh
uv run --no-dev uvicorn --factory gilda.app:create_app --host <host> --port <port> --proxy-headers --forwarded-allow-ips <proxy-address>
```

The command stays on one line, without quotes, so that it pastes whole
into a one-line field; `<proxy-address>` is the address of the
provider's proxy, e.g. `::1`.

- `--factory`: `create_app` builds the app.
- `--no-dev`: otherwise `uv run` installs the development tools again.
- `--proxy-headers`: the site sees the visitors' scheme and address
  through the provider's proxy.

uvicorn, run this way, has no hot restart.

## Deploy a new version

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
