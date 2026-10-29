# Backlog

- Deploy: run Gilda on alwaysdata (site, PostgreSQL, build and migration steps) to check that the stack works where it will actually live.
- Planning: an association timezone, so the server and the screen agree on what today is.
- Sessions: purge expired sessions regularly (Advanced Alchemy's delete_expired), so the user_session table stays small.

## Security

- Session fixation: issue a new session ID at sign-in and sign-up (Litestar reuses the incoming cookie's ID).

## Reliability

- Sign-up fails with a raw 500 if sending the confirmation email fails (e.g. SMTP unreachable); it should fail cleanly instead.
