# Backlog

- Sessions: purge expired sessions regularly (Advanced Alchemy's delete_expired), so the user_session table stays small.
- Mailer: the confirmation email is English-only; send a bilingual (English/French) message instead.
- Planning: with many slots in a day, the narrow-screen Schedule becomes unusable; stack a day's slots vertically in a single column. Also check the wide screen, whose page width is capped. (3–4 slots a day, as at La Fabrique, work today.)
- Planning: a volunteer whose registration becomes obsolete (its slot removed or closed) is told so and acknowledges it; today it silently disappears from their Home summary.
- Association: a manager can remove a member from the association.
- My associations: "You're not a member of any association" shows even when the user has some (its `v-else` hangs on the error message, not on the list).
- Home: show confirmed registrations up to the later of the planning period's end and 27 days ahead, so a period ending soon still shows four weeks.
- Schedule: opening it waits for the planning period before loading the weeks; let `GET …/schedule` default to the range the screen needs (six weeks, extended to the period) so it takes one request.
- Association: a manager can change the association's timezone (fixed to Europe/Paris for now); My associations then needs it in `GET /api/associations`.
- Spec: `GET /api/associations` and My associations sit in the core pages though R12–R14 are planning's; move them to a home page once other modules add their part.

## Security

- Session fixation: issue a new session ID at sign-in and sign-up (Litestar reuses the incoming cookie's ID).

## Quality

- Backend tests: speed up the suite (5 min), e.g. cheaper Argon2 parameters in tests or shared account fixtures.
- Backend: make preference PUT an atomic upsert (ON CONFLICT), so concurrent saves don't return 500.
- Frontend: the logo path is duplicated in App.vue and favicon.svg; share one source.
- Frontend: split ScheduleView into a week grid component and an occurrence menu component, so Schedule changes stay local.
