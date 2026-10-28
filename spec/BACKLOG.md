# Backlog

- Deploy: run Gilda on alwaysdata (site, PostgreSQL, build and migration steps) to check that the stack works where it will actually live.
- Planning: volunteers of an association see and fill the schedule (associations, volunteers, time slots).
- Sessions: purge expired sessions regularly (Advanced Alchemy's delete_expired), so the user_session table stays small.

## Security

- Email verification: confirm a user's email before sign-up sets their password, so nobody can take over a volunteer's email.
- Session fixation: issue a new session ID at sign-in and sign-up (Litestar reuses the incoming cookie's ID).
