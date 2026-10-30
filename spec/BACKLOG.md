# Backlog

- Home: when signed in, `/` shows for each of the user's associations a summary of what concerns them: their next registration and their proposed registrations to confirm.
- Sessions: purge expired sessions regularly (Advanced Alchemy's delete_expired), so the user_session table stays small.
- Mailer: the confirmation email is English-only; send a bilingual (English/French) message instead.
- Planning: with many slots in a day, the narrow-screen Schedule becomes unusable; stack a day's slots vertically in a single column. Also check the wide screen, whose page width is capped. (3–4 slots a day, as at La Fabrique, work today.)
- Association: a manager can change the association's timezone (fixed to Europe/Paris for now).

## Security

- Session fixation: issue a new session ID at sign-in and sign-up (Litestar reuses the incoming cookie's ID).

## Quality

- Frontend: the logo path is duplicated in App.vue and favicon.svg; share one source.
- Frontend: split ScheduleView into a week grid component and an occurrence menu component, so Schedule changes stay local.
