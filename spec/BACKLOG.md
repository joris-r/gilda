# Backlog

- My associations: "You're not a member of any association" shows even when the user has some (its `v-else` hangs on the error message, not on the list).
- Home: show confirmed registrations up to the later of the planning period's end and 27 days ahead, so a period ending soon still shows four weeks.
- Deployment: an "invitation only" setting, so that only emails a manager already added as members can create an account (today anyone can sign up).
- Mailer: the confirmation email is English-only; send a bilingual (English/French) message instead, as every later email will be.
- Accounts: password reset for a forgotten password, by an emailed link.
- Accounts: a very simple sign-in for volunteers: a revocable personal access link, sent by email, signs them in on one click (e.g. on a phone) to manage their registrations; it grants no management rights. (Today the association's shared spreadsheet is a public, writable link.)
- Communication: a manager emails the members on demand, e.g. to send them their access link.
- UX: no inline creation or editing on pages; a button opens a form to create, an icon opens editing. Study it as one consistent design across the pages it affects, before the new forms below.
- Planning: a personal page per association, e.g. "My availability" ("Mes disponibilités"), where a member sets their slot preferences (moved out of Schedule settings), their absence periods, and a note for the managers with standing instructions (e.g. "always group my registrations in pairs").
- Schedule: in the list of members a manager can propose an occurrence to, show who is absent on its date and each member's note on hovering their name (managers are assumed to use a real screen); sort it first by preference for its slot (Preferred, Possible, Unavailable, then absent), then by fewest registrations in the planning period.
- Schedule settings: Members' preferences is unusable at 14 members and 8 slots: it scrolls horizontally and the member names scroll out of view; keep the names visible (e.g. a sticky first column) or rethink the layout.
- Schedule settings: Add slot defaults From to 09:00 (not the current time) and To to the From time; after a slot is added, From defaults to that slot's end.
- Association: a manager can remove a member from the association.
- Planning: a volunteer whose registration becomes obsolete (its slot removed or closed) is told so and acknowledges it; today it silently disappears from their Home summary.
- Frontend: the page width is capped at 640px, cramped on a wide screen; raise the cap (check the Schedule week grid there). The Create an account form is also narrower on a wide screen than on a narrow one.
- Schedule: on a wide screen, drop the times ("10–13") from the occurrence blocks, as the narrow screen does; the menu opened by clicking one already shows them, and the hour axis places it. An unregistered occurrence then shows as an empty red block; the narrow-screen mock-up already shows no times, against the rule that an occurrence shows its times.
- Schedule: make the planning period stand out more than its two marker lines do today, e.g. with a different background for its weeks.
- Planning: with many slots in a day, the narrow-screen Schedule becomes unusable; stack a day's slots vertically in a single column. (3–4 slots a day, as at La Fabrique, work today.)
- Schedule: opening it waits for the planning period before loading the weeks; let `GET …/schedule` default to the range the screen needs (six weeks, extended to the period) so it takes one request.
- Planning: a manager creates a revocable read-only share link to the Schedule, viewable without signing in (e.g. on the association's office PC).
- Admin: a superuser, the account whose email is set in an environment variable; its powers are still to define.
- Association: a manager can change the association's timezone (fixed to Europe/Paris for now); My associations then needs it in `GET /api/associations`.
- Spec: `GET /api/associations` and My associations sit in the core pages though R12–R14 are planning's; move them to a home page once other modules add their part.
- Sessions: purge expired sessions regularly (Advanced Alchemy's delete_expired), so the user_session table stays small.

## Security

- Session fixation: issue a new session ID at sign-in and sign-up (Litestar reuses the incoming cookie's ID).

## Quality

- Backend: make preference PUT an atomic upsert (ON CONFLICT), so concurrent saves don't return 500.
- Backend tests: report to Advanced Alchemy that its Litestar lifespan disposes only the first config's engine per process, then drop the workaround in the new_client fixture.
- Frontend: split ScheduleView into a week grid component and an occurrence menu component, so Schedule changes stay local.
- Frontend: the logo path is duplicated in App.vue and favicon.svg; share one source.
