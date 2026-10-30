# Backlog

- Planning: an association timezone, so the server and the screen agree on what today is.
- Sessions: purge expired sessions regularly (Advanced Alchemy's delete_expired), so the user_session table stays small.
- Hosting: genericize the "alwaysdata" naming in the spec and README (e.g. "provider") if the hosting provider ever becomes a real choice rather than a fixed decision.
- Mailer: the confirmation email is English-only; send a bilingual (English/French) message instead.

## Security

- Session fixation: issue a new session ID at sign-in and sign-up (Litestar reuses the incoming cookie's ID).

## Quality

- Frontend: the logo path is duplicated in App.vue and favicon.svg; share one source.
