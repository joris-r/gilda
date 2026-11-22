# Backlog

## Real use feedback

- it's unclear for volunteer if they need to create an account or ask for password on the first use. Make take would to merge both process.
- breadcrum miss the homepage first step. Also make it sticky on the screen top
- auto scroll on the current day on schedule opening
- improve homepage by seeing more cleary what is coming soon or later 
- pre-filling in slot creation is painful. Better: initally 9:00-10:00, when start change (+X:+Y) move end by the same amount, on new dialog : repeat previous value
- make stand out the user own slot on the schedule (new color?), not sure about that
- sharing of user planning for google agenda or similar

## Fixes

What the software gets wrong today, against the specification or the user.

- Fix: Add/Edit closure refuse a missing label; Propose refuses a non-string user_id instead of answering 500 (/core/operations/general/malformed); remove the xfail marks.
- Delete account: delete the user's other sessions, as /core/operations/delete-account/deleted says (today they are only refused at load).
- Create an account and Forgot password: a failed send keeps the previous link working.
- Frontend: one failed signal per dialog, so a dialog's generic error stops also showing in the screen or menu behind it (the move and cancel dialogs of the Occurrence menu).
- Schedule: after "Someone took this slot in the meantime.", the open Occurrence menu shows the occurrence as it now is, instead of keeping "Sign up" (and a manager's names) until it closes.
- Access pages: when Confirm email succeeds but its answer never reaches the browser, [Try again] says "This link is no longer valid." though the email is confirmed; point to Sign in there.
- Notes: one definition of an empty note (the Occurrence menu says "more than spaces", Set note trims spaces, tabs and line breaks, My availability calls it the empty note).
- Association: refuse a name made only of spaces, at creation and on rename.

## Security

- Access links never expire, so each is a permanent credential in an inbox; decide an expiration (with a `created_at` from their UUIDv7 id) or a stronger scheme.
- CSRF: the actions have no token and rely on the session cookie's SameSite, left to Litestar's default and unchecked; set it explicitly and test it.
- Rate limit: one mechanism for the actions that send an email (Sign-in link, Forgot password, Send link) and those that build up to 520 weeks per request (More weeks, Sign up, Confirm and Cancel registration, public `POST /shared/{token}/weeks`); a lower maximum of weeks would also help.
- Opening someone else's access link silently replaces the current session, so an attacker could get a victim working in the attacker's account; confirm first when signed in as another user.
- /core/operations/reset-password/reset keeps the user's other sessions signed in, so a stolen session survives a password reset; revisit it.
- Sign-in link and Forgot password send their email during the request, so the response time can reveal an account; send it in the background.
- Association deletion: archive first and erase after a delay, so a manager's mistake or a stolen session can be undone.

## Features

- Planning: warn about, or refuse, a closure that overlaps another (the Schedule's Closed line lists every covering closure today).
- Planning: with many slots a day, the narrow-screen Schedule becomes unusable; stack a day's slots in a single column (3–4 a day, as at La Fabrique, work today).
- Orders: My associations lists the associations the user manages first, as Members does.
- Orders: sort names by the interface language's collation, not by case and accents alone (`/ui/name-order` once built); may need a library such as PyICU.
- Association: a manager sets the association's timezone (fixed to Europe/Paris today) and preferred language, used for emails sent to its members by someone else; My associations then needs each association's timezone.
- Association: redirect a former slug to the association; needs a history of slugs, and conflicts with freeing the former slug for another association.
- Frontend: live screens, through a long-lived Datastar SSE stream per screen and a broadcaster (in-process or Postgres LISTEN/NOTIFY), replacing the refresh on return of Members' preferences and the Schedule.
- Cleanup: an association left with no member stays forever, unreachable, with its slug and share link; decide its fate (automatic deletion, or a superuser action, which needs its own screen).
- Cleanup: a procedure to purge old planning data (past absences, registrations, closures), kept forever today.

## Performance

- Compress responses (gzip): pages and static files are sent uncompressed.
- Let browsers cache `/static`, with a versioned URL so a deploy still reaches them.
- Members renders an edit dialog and up to three confirmations per member; shared dialogs filled from the line they open on, as Schedule settings does, keep the page small.
- Members' preferences renders a selector per member and slot, so the page grows with the association.
- More weeks, Sign up, Propose, Confirm and Cancel registration resend every shown week, so each response grows with the weeks shown.
- My associations builds each association's summary with its own queries, so the page slows as a user joins more associations.

## Accessibility

- Audit the screens with a screen reader and axe (e.g. in the e2e tests); the Schedule's occurrence labels, for one, cannot say that a registration is cancelled.
- Make the header's location the `<h1>` of every signed-in screen (only My associations has one); needs a `future` increment first, as `/core/ui/header/title` says only that the location stands for the title.

## Dependencies

- Dependencies: upgrade the bundled Datastar from 1.0.4 to 1.0.5, for its retry and tab visibility fixes (see deps_feedback/datastar-01-retry-defaults/).
- Backend: replace Advanced Alchemy's deprecated repository `list()` (removed in 2.0.0) by `get_many`, then narrow the warning filter of `pyproject.toml` to the library's import-time warnings.
- Tooling: pin the Mailpit image in `compose.yaml` (`latest` today), so a Mailpit change stops breaking the email helpers unannounced (see deps_feedback/mailpit-01-test-quirks/).
- Sessions: drop the `SessionBackend` subclass once Litestar saves only changed sessions and can renew the session ID (see deps_feedback/litestar-01-session-stale-save/).

## Code and tooling

- Backend: a refused Datastar action answers 200, which Advanced Alchemy's autocommit commits, so each handler rolls back by hand (Create an account, Send link); roll back in one place, or check it.
- Frontend: reset `$_failed` once when a dialog opens (a shared macro or a `toggle` listener) instead of in each opener (six had forgotten it); give the actions run on opening (Access link, Confirm email) a shared failure-with-retry component instead of the layout's `after_error` block per page.
- Cleanup: purge expired sessions (Advanced Alchemy's `delete_expired`) and expired email confirmation and password reset tokens regularly.
- Cleanup: one helper for "today in the association's timezone", computed in five places of `planning/services.py`.
- Backend: align the preference unique constraint's name with the model's naming convention, so autogenerated migrations stop proposing to rename it.
- Notices: drop the tab-less notice path if the backend tests are reworked.
- End-to-end: run the suite on Firefox and WebKit too; the menu and dialog rely on `popover`, `commandfor` and CSS anchor positioning.
- Tooling: `make format` runs `ruff format` before `ruff check --fix`, so long lines get wrapped before the check stops.
- Config: rename `FRONTEND_URL`, left from the former frontend, to the site's address (e.g. `SITE_URL`) in the code, the README and the hosting provider's settings, alongside another deploy change.
