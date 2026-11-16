# Backlog

## Real use feedback

- it's unclear for volunteer if they need to create an account or ask for password on the first use. Make take would to merge both process.
- make stand out the user own slot on the schedule (new color?)
- breadcrum miss the homepage first step. Also make it sticky on the screen top
- auto scroll on the current day on schedule opening
- sharing of user planning for google agenda or similar
- pre-filling in slot creation is painful. Better: initally 9:00-10:00, when start change (+X:+Y) move end by the same amount, on new dialog : repeat previous value
- there is a flash with a red text on assocation creation submission
- improve homepage by seeing more cleary what is coming soon or later 

## Main list

- Notes: one definition of whitespace for an empty note: the Occurrence menu says "more than spaces", Set note trims spaces, tabs and line breaks, My availability calls it the empty note.
- Frontend: a failed signal per dialog, so a dialog's generic error does not also show in the screen or menu behind it (the move and cancel dialogs of the Occurrence menu).
- Tests: a clock injected into the services, so tests reach past states without SQL.
- Notices: claim the notice by a one-shot POST so a prefetch or retry cannot consume it (`GET /notice` consumes it today), and drop the tab-less path if the backend tests are reworked.
- Tooling: `make format` runs `ruff format` before `ruff check --fix`, so long lines get wrapped before the check stops.
- End-to-end: a shorter `actionTimeout`, so a suite failing on a missing screen ends fast.
- Tests: the regex page helpers (`lines_of`, `line_of`, `section_of`…) would use an HTML parser, as `listed` does, read only the visible elements and unescape the text, so that nested lists, hidden copies and headings with an apostrophe read right.
- Tests: `shown()` would rebuild the HTML of each `datastar-patch-elements` event from its `data: elements` lines, so pytest reads a patch as the browser does and templates need not be sent on one line.
- Tests: the pytest tests that find a dialog by its position on the page would find it by its name.
- Tests: strengthen weak existing tests found by the migration: the e2e share-link revoke test never asserts "None", the only-member account deletion asserts only status 200, and the Schedule's date order is checked only through the column layout.
- End-to-end: a helper would look up a display name on the Schedule within the menu (`#occurrence-menu`), since occurrences are buttons named after their registrations.
- Process: CLAUDE.md would gain three test rules: a test looks for text within the section or dialog it means, or for its visible copy (replacing the rule on the generic error's hidden copies); a test asserting only an absence also asserts something present; tests read from the database only what no screen shows (ids, rows already erased).
- Config: rename `FRONTEND_URL`, a name left from the former frontend, to the site's address (e.g. `SITE_URL`), in the code, the README and the hosting provider's settings, alongside another deploy change.
- Access pages: when Confirm email succeeds on the server but its answer never reaches the browser, [Try again] shows "This link is no longer valid." though the email is confirmed; a pointer to Sign in there would help.
- Orders: sort names by the interface language's collation, not by case and accents alone (`/ui/name-order` once built); it may need a library such as PyICU.
- Orders: My associations would list the associations the user manages first, as Members does.
- Association: redirect a former slug to the association, which needs a history of slugs and conflicts with freeing the former slug for another association.
- Schedule: after "Someone took this slot in the meantime.", the open Occurrence menu would show the occurrence as it now is, not keep "Sign up" (and a manager's names) until it closes.
- Planning: warn about, or refuse, a closure that overlaps another; the Schedule's Closed line lists every covering closure today.
- Process: CLAUDE.md's rule on the generic error in `main` would say to filter visible elements in Playwright (`.filter({ visible: true })`), as the header's dialogs hold hidden copies (a return to Tests in polish-changed-identifier).
- Tests: stale-screen e2e tests (changed identifier in another tab) for Members role/remove/send-link/revoke-link, the period, closure and share-link dialogs, absence edit/delete, propose and cancel; they share the X-Association mechanism.
- End-to-end: `make test-e2e` would take arguments (e.g. a spec file or a grep) to run one spec.
- End-to-end: `tsc --noEmit` reports three type errors in errors-once.spec.ts (Promise<string[]> not assignable to Promise<void>).
- End-to-end: prune the Playwright tests that repeat what a backend test establishes for the same tag; keep only what the browser alone can observe.


## Quality

- Cleanup: purge expired sessions (Advanced Alchemy's delete_expired) and expired email confirmation and password reset tokens regularly, so their tables stay small.
- Association: refuse a name made only of spaces, at creation and on rename.
- Backend: align the preference unique constraint's name with the model's naming convention, so autogenerated migrations stop proposing to rename it.
- Quality: run Prettier and ESLint on `e2e/` in `make lint`, with a Prettier config matching the project's style (single quotes, no semicolons); `scenarios.spec.ts` is not formatted today, and `members.spec.ts` was formatted with Prettier's defaults.
- Accessibility: make the header's location the `<h1>` of every signed-in screen (only My associations has one today), so screen readers get a heading on each page; needs a `future` increment first, as `/core/ui/header/title` says only that the location stands for the title.
- Frontend: reset `$_failed` once when a dialog opens (a shared macro or a `toggle` listener) instead of in each opener (six had forgotten it), and give the actions that run on opening (Access link, Confirm email) a shared failure-with-retry component instead of the layout's `after_error` block per page.
- Quality: harden the e2e tests of Access link and Confirm email: Try again hidden while the action runs and the running text back after it; Try again failing again on Confirm email; a failure by network abort, not only a 500; and `getByText('My associations')` scoped in the Confirm email test.
- Performance: compress responses (gzip), as pages and static files are sent uncompressed.
- Performance: let browsers cache `/static`, with a versioned URL so a deploy still reaches them.
- End-to-end: run the suite on Firefox and WebKit too; the menu and dialog rely on `popover`, `commandfor` and CSS anchor positioning.
- Accessibility: audit the screens with a screen reader and axe (e.g. in the e2e tests); the Schedule's occurrence labels, for one, cannot say that a registration is cancelled.
- Cleanup: one helper for "today in the association's timezone", computed in five places of planning/services.py.
- Create an account and Forgot password: a failed send keeps the previous link working.
- Backend tests: report to Advanced Alchemy that its Litestar lifespan disposes only the first config's engine per process, then drop the workaround in the new_client fixture.
- Sessions: ask Litestar for a way to renew the session ID (e.g. on `set_session`), then drop the `SessionBackend` subclass.

## Security

- Access links never expire, so each is a permanent credential sitting in an inbox: too weak; decide an expiration (with a `created_at` filled from their UUIDv7 id) or a stronger scheme.
- /core/operations/reset-password/reset keeps the user's other sessions signed in, so someone who stole a session stays connected after a password reset; revisit it.
- Association deletion: archive the association first and erase it after a delay, so a manager's mistake or a stolen session can be undone.
- Rate limit: one mechanism for the actions that send an email (Sign-in link, Forgot password, Send link) and for those that build up to 520 weeks per request (More weeks, Sign up, Confirm and Cancel registration, and the public `POST /shared/{token}/weeks`); a lower maximum of weeks would also help.
- CSRF: the actions have no CSRF token and rely on the session cookie's SameSite setting, left to Litestar's default and unchecked; set it explicitly and test it.
- Sign-in link and Forgot password send their email during the request, so their response time can reveal an account; send it in the background.
- Opening someone else's access link silently replaces the current session, so an attacker could get a victim working in the attacker's account; ask for a confirmation when signed in as another user.

## Future

- Cleanup: a procedure to purge old planning data (e.g. past absences, registrations and closures), which today is kept forever.
- Cleanup: an association left with no member stays forever, unreachable, with its slug and share link; decide its fate (automatic deletion, or a superuser action, which needs its own screen as no screen uses the role today).
- Association: a manager can change the association's timezone (fixed to Europe/Paris for now) and set its preferred language, used for emails sent to its members by someone else (e.g. a manager); My associations then needs each association's timezone.
- Planning: with many slots in a day, the narrow-screen Schedule becomes unusable; stack a day's slots vertically in a single column. (3–4 slots a day, as at La Fabrique, work today.)
- Performance: Members renders an edit dialog and up to three confirmations for every member, so the page grows with the association; shared dialogs filled from the line they are opened on, as Schedule settings does, would fix it.
- Performance: Members' preferences renders a selector for each member and slot, so the page grows with the association.
- Performance: More weeks, Sign up, Propose, Confirm and Cancel registration resend every shown week, so each response grows with the weeks already shown.
- Performance: My associations builds each association's summary with its own queries, so the page slows as a user joins more associations.
- Tooling: e2e should not reuse a server already running on its port, or `make test-e2e` should check the port first.
- Frontend: a long-lived SSE stream per screen (Datastar) with a broadcaster (in-process or Postgres LISTEN/NOTIFY), replacing the refresh on return of Members' preferences and the Schedule, so screens update live.
