# Backlog

- Deploy: run Gilda on alwaysdata (site, PostgreSQL, build and migration steps) to check that the stack works where it will actually live.
- Planning: an association timezone, so the server and the screen agree on what today is.
- Sessions: purge expired sessions regularly (Advanced Alchemy's delete_expired), so the user_session table stays small.
- Hosting: genericize the "alwaysdata" naming in the spec and README (e.g. "provider") if the hosting provider ever becomes a real choice rather than a fixed decision.
- Mailer: mailer.py sends over SMTP (smtplib, TCP) but alwaysdata has no local SMTP listener for that; switch it to hand off to the local `sendmail` binary instead (as apps hosted directly on alwaysdata's servers do), so production email sending actually works without SMTP auth.

## Security

- Session fixation: issue a new session ID at sign-in and sign-up (Litestar reuses the incoming cookie's ID).

## Reliability

- Sign-up fails with a raw 500 if sending the confirmation email fails (e.g. SMTP unreachable); it should fail cleanly instead.
