# Backlog

- Sessions: purge expired sessions regularly (Advanced Alchemy's delete_expired), so the user_session table stays small.
- Mailer: the confirmation email is English-only; send a bilingual (English/French) message instead.
- Planning: with many slots in a day, the narrow-screen Schedule becomes unusable; stack a day's slots vertically in a single column. Also check the wide screen, whose page width is capped. (3–4 slots a day, as at La Fabrique, work today.)
- Planning: a volunteer whose registration becomes obsolete (its slot removed or closed) is told so and acknowledges it; today it silently disappears from their Home summary.
- Association: a manager can change the association's timezone (fixed to Europe/Paris for now); My associations then needs it in `GET /api/associations`.
- Spec: `GET /api/associations` and My associations sit in the core pages though R12–R14 are planning's; move them to a home page once other modules add their part.

## Security

- Session fixation: issue a new session ID at sign-in and sign-up (Litestar reuses the incoming cookie's ID).

## Quality

- Frontend: the logo path is duplicated in App.vue and favicon.svg; share one source.
- Frontend: split ScheduleView into a week grid component and an occurrence menu component, so Schedule changes stay local.
