# Backlog

- Communication: a manager emails the members on demand, e.g. to send them their access link.
- UX: no inline creation or editing on pages; a button opens a form to create, an icon opens editing. Study it as one consistent design across the pages it affects, before the new forms below.
- Planning: a personal page per association, e.g. "My availability" ("Mes disponibilités"), where a member sets their slot preferences (moved out of Schedule settings), their absence periods, and a note for the managers with standing instructions (e.g. "always group my registrations in pairs").
- Schedule: in the list of members a manager can propose an occurrence to, show who is absent on its date and each member's note on hovering their name (managers are assumed to use a real screen); sort it first by preference for its slot (Preferred, Possible, Unavailable, then absent), then by fewest registrations in the planning period.
- Association: a manager can remove a member from the association.
- Planning: a volunteer whose registration becomes obsolete (its slot removed or closed) is told so and acknowledges it; today it silently disappears from their Home summary.
- Frontend: the page width is capped at 640px, cramped on a wide screen; raise the cap (check the Schedule week grid there). The Create an account form is also narrower on a wide screen than on a narrow one.
- Schedule: on a wide screen, drop the times ("10–13") from the occurrence blocks, as the narrow screen does; the menu opened by clicking one already shows them, and the hour axis places it. An unregistered occurrence then shows as an empty red block; the narrow-screen mock-up already shows no times, against the rule that an occurrence shows its times.
- Schedule: make the planning period stand out more than its two marker lines do today, e.g. with a different background for its weeks.
- Planning: with many slots in a day, the narrow-screen Schedule becomes unusable; stack a day's slots vertically in a single column. (3–4 slots a day, as at La Fabrique, work today.)
- Schedule: opening it waits for the planning period before loading the weeks; let `GET …/schedule` default to the range the screen needs (six weeks, extended to the period) so it takes one request.
- Planning: a manager creates a revocable read-only share link to the Schedule, viewable without signing in (e.g. on the association's office PC).
- Association: a manager can change the association's timezone (fixed to Europe/Paris for now) and set its preferred language, used for emails sent to its members by someone else (e.g. a manager); My associations then needs the timezone in `GET /api/associations`.
- Spec: `GET /api/associations` and My associations sit in the core pages though R12–R14 are planning's; move them to a home page once other modules add their part.
- Cleanup: purge expired sessions (Advanced Alchemy's delete_expired) and expired email confirmation and password reset tokens regularly, so their tables stay small.
- API: drop `has_account` from members, which no screen uses since the access link.

## Quality

- Backend tests: report to Advanced Alchemy that its Litestar lifespan disposes only the first config's engine per process, then drop the workaround in the new_client fixture.
- Sessions: ask Litestar for a way to renew the session ID (e.g. on `set_session`), then drop the `SessionBackend` subclass.
