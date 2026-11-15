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

- Tooling: `make format` runs `ruff format` before `ruff check --fix`, so long lines get wrapped before the check stops.
- Tests: the pytest tests that find a dialog by its position on the page would find it by its name.
- End-to-end: a shorter `actionTimeout`, so a suite failing on a missing screen ends fast.
- Process: CLAUDE.md's rule on text lookups would also cover tests asserting that the text is absent (e.g. `NAME not in main`).
- Tests: the core tests' page helpers would also leave out hidden elements, as the planning `section_of` now does.
- Tests: `shown()` would rebuild the HTML of each `datastar-patch-elements` event from its `data: elements` lines, so pytest reads a patch as the browser does and templates need not be sent on one line.
- Process: CLAUDE.md would ask tests that read a screen's lines to look only within their section, so that a new section can't break them.
- Process: CLAUDE.md's rule on the generic error's hidden copies would also cover closed dialogs within `main`: a test of a signed-in screen looks for the visible copy (`.filter({ visible: true })`) or within the section or dialog it means.
- Tests: `section_of` would unescape the HTML before matching a heading, so a heading with an apostrophe needs no `| safe`.
- Process: CLAUDE.md would ask, when a test's read of state moves from a deleted endpoint to a screen, to check that the screen still shows what the test checks (e.g. a removed member's row leaves the screen).
- Process: CLAUDE.md would ask, when an endpoint leaves, to search the tests for its last path segment alone (e.g. `schedule?from=`), as parametrized lists name it without its prefix.
- Process: CLAUDE.md would ask, before planning to keep an endpoint for the backend fixtures, to check what the fixtures do with it, since a new action may already cover their calls (e.g. they only cancel the user's own registrations).
- Process: CLAUDE.md would ask that an e2e lookup of a display name on the Schedule look within the menu (`#occurrence-menu`), since occurrences are buttons named after their registrations.
- Process: CLAUDE.md would note that action tests assert the generic error is absent from the whole response, so a dialog holding its hidden copy stays outside the fragment an action sends back.
- Process: CLAUDE.md would ask that a ported test asserting only an absence also assert something present, so that it fails before the implementation.
- Tests: the regex page helpers (`lines_of`, `line_of`…) would use an HTML parser, as `listed` does, so that nested lists and hidden elements read right.
- Process: CLAUDE.md would say that tests read from the database only what no screen shows (ids, rows already erased), and everything else through the screens.
- Process: CLAUDE.md would ask a setup helper whose action answers a list with dialogs to check success by its message, not by the generic error's absence.
- Tests: strengthen weak existing tests found by the migration: the e2e share-link revoke test never asserts "None", the only-member account deletion asserts only status 200, and the Schedule's date order is checked only through the column layout.
- Config: rename `FRONTEND_URL`, a name left from the former frontend, to the site's address (e.g. `SITE_URL`), in the code, the README and the hosting provider's settings.


## Datastar rewrite feedback

### Possible features or bugs

- End-to-end: run the suite on Firefox too; the menu and dialog rely on `popover`, `commandfor` and CSS anchor positioning.
- Members renders an edit dialog and up to three confirmations for every member, so the page grows with the association; shared dialogs filled from the line they are opened on, as Schedule settings does, would fix it.
- Members' preferences renders a selector for each member and slot, so the page grows with the association.
- More weeks resends every shown week, so each click's response grows with the weeks already shown.
- Sign up, Propose, Confirm and Cancel registration resend every week shown, as More weeks does.
- My associations builds each association's summary with its own queries, so the page slows as a user joins more associations.
- The superuser now only bypasses /core/operations/create-account/not-invited; no screen shows or uses the role otherwise, so a later superuser action (e.g. the Future cleanup entry) needs its own screen.


## Quality

- Cleanup: purge expired sessions (Advanced Alchemy's delete_expired) and expired email confirmation and password reset tokens regularly, so their tables stay small.
- Association: refuse a name made only of spaces, at creation and on rename.
- Association: a manager can change the association's timezone (fixed to Europe/Paris for now) and set its preferred language, used for emails sent to its members by someone else (e.g. a manager); My associations then needs each association's timezone.
- Planning: with many slots in a day, the narrow-screen Schedule becomes unusable; stack a day's slots vertically in a single column. (3–4 slots a day, as at La Fabrique, work today.)
- Backend: align the preference unique constraint's name with the model's naming convention, so autogenerated migrations stop proposing to rename it.
- Quality: run Prettier and ESLint on `e2e/` in `make lint`, with a Prettier config matching the project's style (single quotes, no semicolons); `scenarios.spec.ts` is not formatted today, and `members.spec.ts` was formatted with Prettier's defaults.
- Backend tests: report to Advanced Alchemy that its Litestar lifespan disposes only the first config's engine per process, then drop the workaround in the new_client fixture.
- Accessibility: audit the screens with a screen reader and axe (e.g. in the e2e tests); the Schedule's occurrence labels, for one, cannot say that a registration is cancelled.
- Sessions: ask Litestar for a way to renew the session ID (e.g. on `set_session`), then drop the `SessionBackend` subclass.
- Create an account and Forgot password: a failed send keeps the previous link working.
- Performance: compress responses (gzip), as pages and static files are sent uncompressed.
- Performance: let browsers cache `/static`, with a versioned URL so a deploy still reaches them.

## Security

- Access links never expire; consider an expiration, with a `created_at` filled from their UUIDv7 id.
- /core/operations/reset-password/reset keeps the user's other sessions signed in, so someone who stole a session stays connected after a password reset; revisit it.
- Forgot password shows the same message for everyone, but its response time can reveal an account, as only a user with a password gets an email during the request; send it in the background.
- Delete my account asks for no password, so an unattended or stolen session can erase the account.
- Sign-in link's response time can reveal an account, as the email is sent during the request.
- Sign-in link and Forgot password have no rate limit, so anyone can flood a known address with emails.
- Add a member tells a manager whether an email already has an account, and shows that user's own display name.
- Any manager can demote or remove every other manager, so one manager can take an association over.
- Any manager can send or revoke any member's sign-in link, another manager's included; revoking signs that user out of their link sessions everywhere, not only in this association.
- Send link has no rate limit, so a manager can flood a member with emails.
- Any manager can delete the association, irreversibly, with no password, so one manager or a stolen session can erase it for every member.
- Opening someone else's access link silently replaces the current session, so an attacker could get a victim working in the attacker's account.
- More weeks builds up to 520 weeks per request, with no rate limit, so a member could load the server with repeated long ranges.
- Sign up, Confirm and Cancel registration accept ranges of up to 520 weeks, as More weeks does, with no rate limit.
- The share link shows the members' display names to anyone holding it, signed out and with no expiry, until a manager replaces or revokes it.
- `POST /shared/{token}/weeks` is public and builds up to 520 weeks per request, with no rate limit, so anyone holding a link can load the server.
- `POST /delete-account`, `POST /revoke-access-link`, `POST /association/new`, `POST /association/{slug}/members`, `POST /association/{slug}/members/{user_id}/role`, `POST /association/{slug}/members/{user_id}/remove`, `POST /association/{slug}/members/{user_id}/send-link`, `POST /association/{slug}/members/{user_id}/revoke-link`, `POST /association/{slug}/rename`, `POST /association/{slug}/identifier`, `POST /association/{slug}/delete`, `POST /association/{slug}/settings/slots`, `POST /association/{slug}/settings/slots/{slot_id}/edit` `POST /association/{slug}/settings/slots/{slot_id}/delete`, `POST /association/{slug}/settings/period`, `POST /association/{slug}/settings/period/clear`, `POST /association/{slug}/settings/closures`, `POST /association/{slug}/settings/closures/{closure_id}/edit` `POST /association/{slug}/settings/closures/{closure_id}/delete` `POST /association/{slug}/availability/preferences/{slot_id}`, `POST /association/{slug}/availability/absences`, `POST /association/{slug}/availability/absences/{absence_id}/edit`, `POST /association/{slug}/availability/absences/{absence_id}/delete`, `POST /association/{slug}/availability/note`, `POST /association/{slug}/settings/preferences/{slot_id}/{user_id}`, `POST /association/{slug}/menu`, `POST /association/{slug}/sign-up`, `POST /association/{slug}/propose`, `POST /association/{slug}/registrations/{registration_id}/confirm`, `POST /association/{slug}/registrations/{registration_id}/cancel`, `POST /association/{slug}/settings/share-link`, `POST /association/{slug}/settings/share-link/revoke`, `POST /association/{slug}/summary/{registration_id}/confirm` and `POST /association/{slug}/summary/{registration_id}/cancel` have no CSRF token and rely on the session cookie's SameSite setting, which is unchecked.

## Future

- Cleanup: a procedure to purge old planning data (e.g. past absences, registrations and closures), which today is kept forever.
- Cleanup: one helper for "today in the association's timezone", computed in five places of planning/services.py.
- Cleanup: an association left with no member stays forever, unreachable, with its slug and share link; decide its fate (automatic deletion, or a superuser action).
