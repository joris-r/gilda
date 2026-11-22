# Backend actions resend a request after a network error by default

Material for the maintainers of Datastar.

## Versions

- Datastar 1.0.4 (the browser bundle), with datastar-py 1.0.3
- Reproduced in Chromium, driven by Playwright

## What happens

The backend actions (`@get`, `@post`, `@put`, `@patch`, `@delete`)
share these defaults: `retry: "auto"`, `retryMaxCount: 10`,
`retryInterval: 1000`, `retryScaler: 2`, `retryMaxWait: 30000`.

- **A network error is resent, whatever `retry` says.** When `fetch`
  throws (connection refused, reset, closed without a response,
  offline), the catch block schedules a retry unless the request was
  aborted. It does not read `retry`. So `retry: "never"` still resends
  after a network error, up to `retryMaxCount` times. Only
  `retryMaxCount: 0` stops it.
- **An HTTP error is not resent under `"auto"`.** A 4xx or 5xx is
  resent only with `retry: "error"` or `"always"`.
- **The method makes no difference.** A `@post`, `@put`, `@patch` or
  `@delete` is resent just like a `@get`, although the server may
  already have applied it: the connection can drop after the server
  committed and before the response arrived.
- **A `@get` is resent when the tab comes back.** With
  `openWhenHidden: false`, the default for `@get` only, a `@get` still
  in flight is aborted when the tab is hidden and sent again when it
  becomes visible. `retryMaxCount: 0` does not change this.
- **The resends come late.** With the defaults, they come at about 1,
  3, 7, 15 and 31 s, then every 30 s, ten in all: the last one about
  three minutes after the user acted.
- **No setting applies to every action.** The options can only be
  given action by action.

These defaults suit a long-lived SSE stream that should reconnect.
They do not suit the one-shot actions most pages are made of: a form
submit, a button, a selector.

## Effects

- **An operation is applied twice.** A request that went through but
  whose response was lost is applied again: an item added twice, or a
  create that comes back as "already taken".
- **A cancelled action goes through later.** A user opens a
  confirmation dialog, confirms, gets a network error, and cancels.
  A minute later the resend reaches the server and does what the
  user cancelled.
- **An old choice overwrites a newer one.** A preference selector
  changed twice: the first save fails and is resent after the second,
  so the first choice wins.
- **Hard to see in tests.** End-to-end tests that cut the network or
  abort a request see extra requests seconds after the test thinks the
  action is over, and fail intermittently.

## Minimal reproduction

Save the script next to Datastar's `datastar.js` and run
`python3 repro.py datastar.js`. Open http://127.0.0.1:8000/ and click
each button once. The server answers every POST by closing the
connection, so `fetch` fails with a network error.

```python
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGE = b"""<!doctype html>
<script type="module" src="/datastar.js"></script>
<button id="default" data-on:click="@post('/act?case=default')">default</button>
<button id="never" data-on:click="@post('/act?case=never', {retry: 'never'})">retry: never</button>
<button id="zero" data-on:click="@post('/act?case=zero', {retryMaxCount: 0})">retryMaxCount: 0</button>
"""
DATASTAR = Path(sys.argv[1]).read_bytes()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body, kind = (DATASTAR, "text/javascript") if self.path == "/datastar.js" else (PAGE, "text/html")
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Reads the request, then closes the connection without answering:
        # the browser's fetch fails with a network error.
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        print("POST", self.path, flush=True)
        self.close_connection = True

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
```

Requests received in the 9 s after one click on each button:

```
      4 POST /act?case=default
      4 POST /act?case=never
      1 POST /act?case=zero
```

`retry: "never"` behaves like the default.

## What it cost us

Our application needs every operation to be sent once per user
action: after a failure, nothing resends it until the user acts again.
Doing that took:

- `retryMaxCount: 0` written by hand on each of the 47 actions of our
  templates, each with a comment saying why;
- a lint script that fails on any action without it, because a new
  action easily misses it;
- end-to-end tests that make each send of an action fail, on the
  network and on the server, then check that only one send arrives;
- test helpers that wait for the `finished` event of `datastar-fetch`
  rather than for a fixed time, as that event comes only once an
  action can no longer retry.

## What upstream could do

- **Make `retry: "never"` mean never.** Have the network-error path
  read `retry` too, and document which failures each value covers.
- **Do not resend non-idempotent methods by default.** Retry `@post`,
  `@patch` and `@delete` by default only for a stream that already
  started, or not at all; keep reconnection for `@get` streams.
- **Allow global defaults.** One place, such as an attribute on the
  script or the root element, or a call before start, to set the fetch
  options of every action, so that an application sets
  `retryMaxCount: 0` once.
- **Document the defaults.** The docs could say that a one-shot action
  is resent up to ten times over several minutes after a network
  error, and that a `@get` is sent again when the tab becomes visible.
