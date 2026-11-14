# Backlog

## Real use feedback

- pre-filling in slot creation is painful. Better: initally 9:00-10:00, when start change (+X:+Y) move end by the same amount, on new dialog : repeat previous value
- there is a flash with a red text on assocation creation submission

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
- Specification: a General statement on roles, as planning's `[member]` does for membership, so that the `[volunteer]` refusal leaves the nine ordered lists it opens, most of which then become exclusive.
- Config: rename `FRONTEND_URL`, a name left from the former frontend, to the site's address (e.g. `SITE_URL`), in the code, the README and the hosting provider's settings.


## Datastar rewrite feedback

### Possible spec updates

Choices the spec left open, settled by `forgot-password`:

- Reset password: a short password with a bad link shows the generic error first, as the password is checked before the token.
- Reset password: a missing token on submit shows the invalid link.
- Forgot password: "Back to Sign in" stays under the message once the form is submitted.

Choices the spec left open, settled by `delete-account`:

- Delete my account: a request that is already signed out leads to Sign in.

Choices the spec left open, settled by `header`:

- Revoke my sign-in link: with no link, it shows the same "revoked" message.
- Revoke my sign-in link: a request that is already signed out leads to Sign in.
- Revoke my sign-in link: the message stays until the page reloads.

Choices the spec left open, settled by `sign-in-link`:

- Sign-in link: "Back to Sign in" stays under the message once the form is submitted.
- Access link: a missing token shows the invalid link.
- Access link: opening a link in another user's session signs in as the link's user.
- Access link: the page runs the sign-in once it loads, so fetching the link alone signs no one in.

Choices the spec left open, settled by `my-associations`:

- New association: an empty or missing name or identifier shows the generic error.
- New association: a request that is already signed out leads to Sign in and creates nothing.
- New association: the identifier `new` shows the "already taken" message.
- /core/model/association/derived: an identifier cut at 50 characters loses a hyphen left at its end.

Choices the spec left open, settled by `members-list`:

- Add a member: a missing or invalid field, including the role, shows the generic error.
- Add a member: "is already a member" names the person as typed; "added" names them as listed, so an existing user (/core/operations/add-member/existing-user) shows under their own display name.
- Add a member: a request that is already signed out leads to Sign in and adds no one; a volunteer's or a non-member's request adds no one.
- Add a member: opening the dialog clears its fields and its message.
- Add a member: Email accepts an address with accents, as the browser does not check it.
- Members: an unknown association, or one the user is not a member of, answers 200 with its message.
- Members: display names are ordered ignoring case.

Choices the spec left open, settled by `members-edit`:

- Edit dialog: a missing or invalid role, or a user who is not a member, shows the generic error.
- Edit dialog: a request that is already signed out leads to Sign in and changes nothing; a volunteer's or a non-member's request changes nothing.
- Edit dialog: opening it shows the member's current role and clears its message and the generic error.
- Remove from the association: removing the last manager closes the confirmation and shows the message in the edit dialog.
- Save: a manager who demotes themself stays on Members, which then shows no edit icons and no "Add a member".

Choices the spec left open, settled by `members-link`:

- Send link and Revoke link: a user who is not a member shows the generic error.
- Send link and Revoke link: a request that is already signed out leads to Sign in and changes nothing; a volunteer's or a non-member's request changes nothing.
- Send link: when the email can't be sent, no link is created, so Revoke link does not appear; the message shows in the edit dialog, closing the confirmation.
- Send link and Revoke link: success closes the dialogs and shows the message on Members, with Revoke link appearing or leaving at once.

Choices the spec left open, settled by `members-association`:

- Rename the association: a missing or empty name shows the generic error; a name that only another association has is accepted.
- Change the association identifier: a missing slug shows the generic error; a malformed slug is refused before a taken one.
- Rename and Change the association identifier: a request that is already signed out leads to Sign in and changes nothing; a volunteer's or a non-member's request changes nothing and shows the generic error.
- Delete the association: only the button checks the typed name; the server deletes on any manager's request.
- Delete the association: a volunteer's or a non-member's request deletes nothing and reloads Members as it now is.
- Change the association identifier and Delete the association: their message shows once, on the next page loaded.

Choices the spec left open, settled by `settings-slots`:

- Add a slot and Edit the slot: a missing or invalid field, To not after From included, shows the generic error.
- Add a slot: Day opens at Monday until a slot is added; /planning/ui/schedule-settings/next-slot lasts until the page reloads, which brings back /planning/ui/schedule-settings/defaults.
- Add a slot: reopened after Cancel, it opens as /planning/ui/schedule-settings/defaults or /planning/ui/schedule-settings/next-slot say, not with what was typed.
- Edit the slot and Delete the slot: an unknown slot, or another association's, shows the generic error.
- Add, Edit and Delete the slot: a request that is already signed out leads to Sign in and changes nothing; a volunteer's or a non-member's request changes nothing and shows the generic error.

Choices the spec left open, settled by `settings-closures-period`:

- Planning period: the dialog opens filled with the period, or empty when there is none.
- Planning period, Add a closure and Edit the closure: a missing or invalid date shows the generic error, including To before From.
- Add a closure: opens empty, also after Cancel or after an add.
- Add a closure and Edit the closure: an empty or blank Label saves the closure without a label.
- A one-day closure or period shows one date; a longer one shows "first – last".
- Edit the closure and Delete the closure: an unknown closure, or another association's, shows the generic error.
- Planning period, Clear, and the closure actions: a request that is already signed out leads to Sign in and changes nothing; a volunteer's or a non-member's request changes nothing and shows the generic error.

Choices the spec left open, settled by `availability-preferences`:

- My preferences: a missing or invalid value, an unknown slot or another association's slot shows the generic error.
- My preferences: "—" on a slot with no preference changes nothing.
- My preferences: a request that is already signed out leads to Sign in and changes nothing; a non-member's request changes nothing.

Choices the spec left open, settled by `availability-absences-note`:

- Add an absence and Edit the absence: a missing or invalid date shows the generic error, including To before From.
- Add an absence: opens empty, also after Cancel or after an add.
- A one-day absence shows one date, also in "Delete the absence of …?".
- Edit the absence and Delete the absence: an unknown absence, another member's or another association's shows the generic error.
- Absences: "today" is the association's timezone's.
- Note for the managers: the dialog opens with the note as last saved, also after a Save or a Cancel; the note keeps its lines; a note of only spaces shows "None".
- Absences and the note: a request that is already signed out leads to Sign in and changes nothing; a non-member's request changes nothing.

Choices the spec left open, settled by `settings-preferences`:

- Members' preferences: with no slot, it shows "None".
- Members' preferences: a column shows its slot with the short weekday, "Thu 10:00–13:00" ("jeu." in French), as dates do.
- Members' preferences: adding, editing or deleting a slot updates its columns at once.
- Members' preferences: a missing or invalid value, an unknown slot or one of another association, or a user who is not a member shows the generic error.
- Members' preferences: a volunteer's request, even for their own preference, changes nothing and shows the generic error; a request that is already signed out leads to Sign in and changes nothing; a non-member's request changes nothing.

Choices the spec left open, settled by `schedule-weeks`:

- Schedule: week headings show the ISO week number ("Week 53", then "Week 1").
- Schedule: the lines show the date in full ("Monday 9 November 2026", "lundi 9 novembre 2026"); day heads show it short, without the year ("Thu 29 Oct", "jeu. 29 oct.").
- Schedule: the time scale has a mark for every hour; on a narrow screen, every other mark is hidden past six hours.
- Schedule: an obsolete registration gives its weekday a column, as an occurrence does.
- Schedule: an occurrence's accessible label is its times, then what it shows, e.g. "10–13 Chloé ?".
- More weeks: a missing, invalid or reversed range, or one over 520 weeks, shows the generic error; a non-member's request shows none of the weeks; a request that is already signed out leads to Sign in.

Choices the spec left open, settled by `schedule-volunteer-menu`:

- Schedule menu: a missing or invalid date or time, or no occurrence at that time, opens the menu with only the generic error.
- Sign up: a date before today (/planning/operations/register/past), no matching occurrence, a closed date or a missing field shows the generic error; only /planning/operations/register/taken has its own message, "Someone took this slot in the meantime."
- Confirm and Cancel registration: an unknown registration, or another association's, shows the generic error.
- Menu, Sign up, Confirm and Cancel registration: a request that is already signed out leads to Sign in and changes nothing; a non-member's request changes nothing.
- Schedule menu: the user's own obsolete registration offers Cancel registration, whether proposed or confirmed, and never Confirm.

Choices the spec left open, settled by `schedule-manager-menu`:

- Absence icon: a one-day absence shows one date, "Absent Thu 12 Nov 2037" ("Absent le jeu. 12 nov. 2037"); when several absences cover the date, the one starting first shows.
- Propose: a user who is not a member, a missing or invalid field, a date before today, a closed date, or a volunteer proposing to another member shows the generic error; only /planning/operations/register/taken has its own message.
- Propose: a request that is already signed out leads to Sign in and registers no one; a non-member's request registers no one.
- Manager's menu: without a planning period, /planning/ui/occurrence-menu/order's tie on registrations counts everyone as 0, so names fall to display name order, ignoring case.
- Manager's menu: the text shown under the names leaves when the menu opens again.

Choices the spec left open, settled by `share-link`:

- Share link: it shows the absolute URL, built from the site's address as the emails' links are.
- Share link: "Link copied." stays until the next Create, Replace or Revoke, or a reload.
- Create a share link, Replace and Revoke: a request that is already signed out leads to Sign in and changes nothing; a volunteer's or a non-member's request changes nothing and shows the generic error.
- Shared schedule: an unknown, replaced or revoked link answers 200 with its message, under the signed-out header without the association's name.
- Shared schedule: More weeks with a missing or invalid range, or a link no longer valid, shows the generic error.

Choices the spec left open, settled by `registrations-summary`:

- Confirm and OK: an unknown registration, another association's, someone else's, one already cancelled, or a Confirm on a registration that is obsolete or already confirmed shows the generic error.
- Confirm and OK: a request that is already signed out leads to Sign in and changes nothing; a non-member's request changes nothing.
- Confirm and OK: the generic error shows within that association's item, and stays until the next successful action on it or a reload.
- /home/ui/my-associations/no-registration: a one-day planning period shows one date ("5 Nov").

Choices the spec left open, settled by `finish-rewrite`:

- Not found: any method (POST, PUT, DELETE…) on a path that leads nowhere answers the Not found page, `/api/…` paths included.

### Possible features or bugs

- Datastar: after a network error, `@post` retries even once its dialog is cancelled, so a failed "Delete my account" could still go through after Cancel; `retry: 'never'` covers only HTTP errors, and only `retryMaxCount: 0` stops it, as the confirmation macro does.
- Actions outside a confirmation (Sign out, Create an account, Forgot password…) still retry after a network error, so they could run twice.
- Confirmation: the generic error probably still shows after Cancel and reopening, until the next try.
- Revoke my sign-in link: the menu offers it to a user who has no link, and then says "revoked"; consider showing it only when they have one.
- Access link and Confirm email: the page stays blank while the action runs, and after a server failure only the generic error shows, with no way forward.
- Sign-in link: when the email can't be sent, the link is still created, so the member later shows "Revoke link" for a link nobody received.
- End-to-end: run the suite on Firefox too; the menu and dialog rely on `popover`, `commandfor` and CSS anchor positioning.
- New association: its mockup shows a title in the page, but `interface.md` says the header's location stands for the title; the page follows the mockup.
- My associations: the spec sets no order, so the list follows whatever order the database returns.
- New association: "+ New association" is a link, while `interface.md` describes a button.
- Members: display names are ordered by `casefold`, not by the language's collation, so "Émile" comes after "Zoé".
- Members renders an edit dialog and up to three confirmations for every member, so the page grows with the association; shared dialogs filled from the line they are opened on, as Schedule settings does, would fix it.
- Revoke link from a page opened before the member's link was revoked elsewhere still says "revoked".
- Send link drops the link when the email can't be sent, but Sign-in link keeps it; align the two.
- The one-time notice is kept in the session, so it shows on whichever page loads next, even in another tab.
- Rename and Delete check against the name the page was loaded with: after a rename in another tab, Delete stays disabled for the new name until a reload.
- Change the association identifier breaks every bookmark of the former URLs, with no redirect (/core/operations/update-association/new-slug).
- Add a slot or Edit the slot with To not after From shows only the generic error; the former frontend said "Check the dates and times: the start comes before the end."
- Edit the slot and Delete the slot don't warn that the slot's registrations become obsolete, nor that deleting it deletes the members' preferences on it.
- Closures: past closures stay listed forever; they could be listed from those ending today on, as Absences are.
- Closures may overlap each other, with no warning.
- Add a closure, Edit the closure and Delete the closure don't warn that the registrations on the closed dates become obsolete, or stop being obsolete.
- Planning period and closures with To before From show only the generic error, as Slots do.
- My preferences: a selector retries after a network error, so a late retry could overwrite a newer choice on the same slot.
- My preferences: when saving fails, the selector keeps the value chosen though it was not saved.
- Adding or editing an absence that ends before today saves it, but it never shows, with no message.
- Absences may overlap each other, with no warning.
- Absences with To before From show only the generic error; the former frontend said "Check the dates: the start comes before the end." (its translation is gone with the former frontend's other leftovers).
- A note of only spaces is saved as is; the Schedule's note icon (a later item) should treat it as empty.
- Members' preferences: when saving fails, the selector keeps the value chosen though it was not saved, as in My preferences.
- Members' preferences: a member added on Members, or a choice made on My availability, shows only after a reload.
- Members' preferences renders a selector for each member and slot, so the page grows with the association.
- Schedule: a page left open past midnight keeps the old today line and past days until it reloads.
- Schedule: a closure on a weekday with no column of the shown weeks doesn't show at all.
- More weeks resends every shown week, so each click's response grows with the weeks already shown.
- Schedule menu: it opens only once the server answers, so a slow network shows nothing for a while after the click.
- Schedule menu: it shows centred on the screen, not anchored to the occurrence.
- Sign up: after "Someone took this slot in the meantime.", the Schedule still shows the occurrence as free until a reload.
- Schedule: a page left open past midnight still offers Sign up on yesterday's occurrences, which then shows only the generic error.
- Cancel registration: the server cancels a registration dated before today (/planning/operations/change-registration/cancel doesn't forbid it), though no menu opens there.
- Sign up, Propose, Confirm and Cancel registration resend every week shown, as More weeks does.
- Manager's menu: names are ordered by `casefold`, not by the language's collation, as on Members.
- Note icon: the whole note is the icon's accessible name, so a long note gives a long screen-reader label.
- Manager's menu: a taken occurrence offers no names, so moving it to another member takes a cancel, then a proposal.
- Shared schedule: once the link is replaced or revoked, More weeks on a page already open shows only the generic error, not "This link is no longer valid.".
- Share link: "Link copied." shows even when the browser refuses the clipboard.
- My associations shows dates without their year, so a proposal months ahead (e.g. "Sun 3 Jan") is ambiguous.
- Confirm and OK use the slug from page load, so after a change of identifier in another tab they show only the generic error.
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
