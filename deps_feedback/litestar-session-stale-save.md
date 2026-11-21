# Server-side sessions: a concurrent request saves back a stale copy

Material for the maintainers of Litestar and Advanced Alchemy.

> **Disclosure.** This defect has a security impact (see Security
> impact). Report it privately, through a GitHub private security
> advisory, rather than in a public issue: to Litestar, for the
> middleware and `ServerSideSessionBackend`, and to Advanced Alchemy,
> for the upsert in `SQLAlchemyAsyncSessionBackend.set` that recreates
> a deleted row.

## Versions

- Python 3.13.12
- litestar 2.25.0
- advanced-alchemy 1.12.0, with `SQLAlchemyAsyncSessionBackend` over
  PostgreSQL (asyncpg 0.32.0)

The reproduction below uses only Litestar and its `MemoryStore`.

## What happens on every request

- `SessionMiddleware.__call__` (`litestar/middleware/session/base.py`)
  loads the session for every request in its scopes, which by default
  covers every HTTP request, static files included. It puts the loaded
  dict in `scope["session"]`.
- Its send wrapper calls `backend.store_in_message(scope["session"], ...)`
  on every `http.response.start`. It does not check whether the
  handler read or changed the session.
- `ServerSideSessionBackend.store_in_message`
  (`litestar/middleware/session/server_side.py`):
  - session `Empty` (after `clear_session()`): deletes the stored
    session and sets a `null` cookie;
  - otherwise: serializes the whole dict, calls `set(session_id, data)`,
    and sends `Set-Cookie` with that session id.
- `set` creates the key if it is missing:
  - `MemoryStore.set` assigns the key;
  - `SQLAlchemyAsyncSessionBackend.set`
    (`advanced_alchemy/extensions/litestar/session.py`) is an upsert
    (`ON CONFLICT ... DO UPDATE`, or a MERGE, or select-then-insert).
- A request without a session cookie gets a newly generated id, and
  its empty dict is stored under it. Every anonymous request, a static
  file included, therefore writes a session row and sets a cookie.

So every response writes back the full copy its request loaded when it
started, under the id that request came with, whether or not the
session changed, and whether or not the session still exists.

## Effects

When two requests of the same session overlap, the one that finishes
last overwrites what the other did:

- **Sign-out undone.** A sign-out deletes the session. A request that
  loaded the session before the deletion and responds after it upserts
  the session back. It also sends `Set-Cookie` with the old id, so the
  browser is signed in again.
- **Session rotation undone.** An application that issues a new id at
  sign-in and deletes the old one has the same problem. A request that
  is in flight with the old cookie recreates the old session and
  points the browser's cookie back at it.
- **Stale keys restored.** A key removed by one request, for example a
  one-time message consumed on display, comes back when an overlapping
  request writes its older copy.
- **No change needed to trigger it.** The overlapping request needs
  only to pass through the middleware: a static file such as a
  favicon, or any read-only page.

## Security impact

This applies to any application that uses Litestar's server-side
sessions. Exploiting it needs no special access: only ordinary
parallel requests from the same browser, which every page with
assets makes.

- **Sign-out does not hold.** A sign-out while other requests of the
  session are in flight can be undone. On a shared device, the user
  who signed out stays signed in.
- **Rotation at sign-in can be undone.** An application that issues a
  new session id at sign-in, against session fixation, can have the
  old session recreated and the cookie pointed back at it, by a
  request still in flight with the old id.
- **Revocation can be defeated.** A session deleted on the server
  (signed out elsewhere, revoked by an administrator, deleted with its
  account or with a password change) is recreated by any of its
  requests still in flight, static files included. A client that
  keeps a request in flight at all times keeps the session alive. So
  someone holding a stolen session id can outlive its revocation.

## Minimal reproduction

The script runs with `litestar` and `httpx` installed. A slow
read-only request loads the session. While it waits, another request
changes or deletes the session. Then the slow request finishes.

```python
import asyncio
from typing import Any

import httpx
from litestar import Litestar, Request, get, post
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore

slow_started = asyncio.Event()
release_slow = asyncio.Event()


@post("/login")
async def login(request: Request[Any, Any, Any]) -> None:
    request.set_session({"user": "alice", "notice": "Saved."})


@post("/logout")
async def logout(request: Request[Any, Any, Any]) -> None:
    request.clear_session()


@post("/claim")
async def claim(request: Request[Any, Any, Any]) -> str:
    notice = request.session.pop("notice", "")
    request.set_session(dict(request.session))
    return notice


@get("/slow")
async def slow(request: Request[Any, Any, Any]) -> None:
    # Reads nothing and writes nothing; stands for a static file or any slow read.
    slow_started.set()
    await release_slow.wait()


@get("/whoami")
async def whoami(request: Request[Any, Any, Any]) -> dict[str, Any]:
    return dict(request.session)


app = Litestar(
    [login, logout, claim, slow, whoami],
    middleware=[ServerSideSessionConfig().middleware],
    stores={"sessions": MemoryStore()},
)


async def race(client: httpx.AsyncClient, action: str) -> Any:
    slow_started.clear()
    release_slow.clear()
    slow_task = asyncio.create_task(client.get("/slow"))  # loads the session
    await slow_started.wait()
    await client.post(action)  # changes or deletes the session
    release_slow.set()
    await slow_task  # saves back the copy it loaded
    return (await client.get("/whoami")).json()


async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/login")
        await client.post("/claim")
        print("control, claim alone:", (await client.get("/whoami")).json())
        await client.post("/logout")
        print("control, logout alone:", (await client.get("/whoami")).json())

        await client.post("/login")
        print("after claim racing a read:", await race(client, "/claim"))
        print("after logout racing a read:", await race(client, "/logout"))


asyncio.run(main())
```

Output:

```
control, claim alone: {'user': 'alice'}
control, logout alone: {}
after claim racing a read: {'user': 'alice', 'notice': 'Saved.'}
after logout racing a read: {'user': 'alice', 'notice': 'Saved.'}
```

With `SQLAlchemyAsyncSessionBackend` in place of `MemoryStore`, the
result is the same, because its `set` is an upsert.

## Measured in a real application

The setup was Advanced Alchemy's backend on PostgreSQL, driven by
Playwright request contexts. Each attempt ran one session request
alongside 8 concurrent `GET` requests for a static favicon in the same
session:

- A one-time message, consumed by a `GET`, was back in the session
  afterwards in 38 of 40 attempts. Without the favicon requests: 0 of
  40.
- A sign-out (`POST`, `clear_session()`) was undone in 20 of 20
  attempts. Without the favicon requests: 0 of 20.

In browsers this showed up as intermittent end-to-end test failures:
a message showing twice, or a sign-out that did not hold.

## What we do in our subclass

We subclass `SQLAlchemyAsyncSessionBackend`. The subclass already
replaced the session id on sign-in, because Litestar keeps the
incoming cookie's id. It now overrides two methods:

- `load_from_connection` calls the parent, then keeps the serialized
  copy it loaded in `connection.state`. When the cookie names no stored
  session, it keeps `None`.
- `store_in_message` no longer calls the parent:
  1. After `clear_session()`, it deletes the session the cookie names
     and expires the cookie, as before.
  2. When the session equals the copy loaded at the start of the
     request, it writes nothing and sends no `Set-Cookie`. This covers
     every static file and read-only page, and an empty session for a
     request without a cookie.
  3. When the request loaded a stored session and changed it, it writes
     the data with an `UPDATE ... WHERE session_id = ... RETURNING
     session_id`. It sets the cookie only if a row was updated. A
     session deleted in the meantime stays deleted, and its id is not
     sent back.
  4. Otherwise (a sign-in, or a change in a request whose cookie named
     no stored session), it inserts the session under a newly
     generated id. On sign-in, it deletes the session the cookie named.
- It builds the `Set-Cookie` header itself, from the config's cookie
  parameters. The cookie's `Max-Age` is set apart from the session's
  `max_age`. Responses that change nothing no longer refresh the
  cookie, so a cookie tied to the session's `max_age` would expire
  that long after the last change, even for a session in daily use.
  `SQLAlchemyAsyncSessionBackend.get` already pushes `expires_at` back
  on every read, so the stored session still expires only once it has
  gone unused for `max_age`.

One pitfall came up. The session backend writes through its own
database connection, and `store_in_message` runs on
`http.response.start`, before the plugin's `autocommit`
`before_send_handler` commits the request's transaction. A request
that deletes its own session row in its transaction (for example, a
bulk delete of the sessions opened by a revoked credential) and then
clears or changes its session waits forever on that row's lock. We
run such deletes on a connection of their own, committed at once.

When two requests that both change the session overlap, the one that
finishes last still writes its whole copy. We accept that for our use.
A key-by-key merge under a row lock would close that gap too.

## What upstream could do

- **Save only a changed session.** The middleware or the backend keeps
  the loaded data, or a hash or dirty flag on the session dict, and
  skips `store_in_message` and its `Set-Cookie` when nothing changed.
  An option such as `save_on_change_only` would keep the current
  behavior available. The cookie's lifetime would then need its own
  setting, apart from the stored session's `max_age`, or sliding
  expiry would be lost.
- **Never resurrect a deleted session.** When the request came with an
  existing id, the store should update the session, not upsert it.
  Creating a key should be reserved for an id generated during the
  request. For `Store`-based backends, this needs an "update if
  exists" operation, or a compare-and-set.
- **Do not store empty sessions.** A request that came without a
  cookie and leaves the session empty needs no stored session and no
  cookie.
- **Rotate the session id.** An API to issue a new id, for example on
  `set_session`, that deletes the old session. Applications need this
  at sign-in to prevent session fixation, and today it takes a
  subclass.
- **Document the behavior.** The docs could state that the session is
  saved on every response, and that static routes go through the
  session middleware unless they are excluded
  (`exclude` / `exclude_opt_key`).
