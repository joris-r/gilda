# session-rotation: sign-in issues a new session ID

Signing in replaces the session ID the browser came with.

## POST /api/session

Added to its rules:

- R16: On success, the `session` cookie set holds a new value, and the
  session ID the request came with, if any, no longer authenticates.
