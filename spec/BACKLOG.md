# Backlog

## Main list

- Tooling: `make format` runs `ruff format` before `ruff check --fix`, so long lines get wrapped before the check stops.
- Tests: the pytest tests that find a dialog by its position on the page would find it by its name.


## Datastar experiment

Rebuild, in this order; each item moves its rules out of the `api.md` pages, ports its tests, deletes its endpoints where no later item needs them, and restores its scenario once its screens are all back:

- Members: Rename the association, Change the association identifier and Delete the association.
- Schedule settings: Slots, with R17 and R18.
- Schedule settings: Closures and Planning period.
- My availability: My preferences.
- My availability: Absences and Note for the managers.
- Schedule settings: Members' preferences.
- Schedule: the weeks read-only, "More weeks", the today and period lines, closures.
- Schedule: the volunteer's menu (Sign up, Confirm, Cancel registration).
- Schedule: the manager's menu (propose, cancel, preferences and counts, absence and note icons); restores "The schedule is filled".
- Schedule settings: Share link, and Shared schedule; restores "The schedule is shared".
- My associations: the registrations summary (R12, R13, R14, Confirm, OK, Choose your slots).
- Finish: delete what remains of the JSON API and the `api.md` pages, the temporary pieces and "Rebuild in progress".


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
- R35: an identifier cut at 50 characters loses a hyphen left at its end.

Choices the spec left open, settled by `members-list`:

- Add a member: a missing or invalid field, including the role, shows the generic error.
- Add a member: "is already a member" names the person as typed; "added" names them as listed, so an existing user (R3) shows under their own display name.
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

### Possible features or bugs

- Reset password: no test checks `superuser` right after a reset since `POST /api/accounts/password-reset/confirm` left; `GET /api/session` should report it.
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
- Members: no served screen links to it yet; only its URL leads there until the Schedule returns.
- Members: display names are ordered by `casefold`, not by the language's collation, so "Émile" comes after "Zoé".
- Members renders an edit dialog and up to three confirmations for every member, so the page grows with the association.
- Revoke link from a page opened before the member's link was revoked elsewhere still says "revoked".
- Send link drops the link when the email can't be sent, but Sign-in link keeps it; align the two.


## Quality

- Spec: `GET /api/associations` and My associations sit in the core pages though R12–R14 are planning's; move them to a home page once other modules add their part.
- Cleanup: purge expired sessions (Advanced Alchemy's delete_expired) and expired email confirmation and password reset tokens regularly, so their tables stay small.
- API: drop `has_account` from members, which no screen uses since the access link.
- Association: refuse a name made only of spaces, at creation and on rename.
- Association: a manager can change the association's timezone (fixed to Europe/Paris for now) and set its preferred language, used for emails sent to its members by someone else (e.g. a manager); My associations then needs the timezone in `GET /api/associations`.
- Planning: with many slots in a day, the narrow-screen Schedule becomes unusable; stack a day's slots vertically in a single column. (3–4 slots a day, as at La Fabrique, work today.)
- Backend: align the preference unique constraint's name with the model's naming convention, so autogenerated migrations stop proposing to rename it.
- Quality: run Prettier and ESLint on `e2e/` in `make lint`, with a Prettier config matching the project's style (single quotes, no semicolons); `scenarios.spec.ts` is not formatted today, and `members.spec.ts` was formatted with Prettier's defaults.
- End-to-end: the sign-up and sign-in helpers are repeated across spec files; move them to `helpers.ts`.
- Backend tests: report to Advanced Alchemy that its Litestar lifespan disposes only the first config's engine per process, then drop the workaround in the new_client fixture.
- Accessibility: audit the screens with a screen reader and axe (e.g. in the e2e tests); the Schedule's occurrence labels, for one, cannot say that a registration is cancelled.
- Sessions: ask Litestar for a way to renew the session ID (e.g. on `set_session`), then drop the `SessionBackend` subclass.
- Spec: separate invariants (data model) from post-conditions (API), with no sentence mixing both, starting with R8, R23, R28 and R33.
- Create an account and Forgot password: a failed send keeps the previous link working.
- Traceability: try named markers on data model rules, with a generated spec-to-tests index, to judge it for Dev43.

## Security

- Access links never expire; consider an expiration, with a `created_at` filled from their UUIDv7 id.
- R22 keeps the user's other sessions signed in, so someone who stole a session stays connected after a password reset; revisit it.
- Forgot password shows the same message for everyone, but its response time can reveal an account, as only a user with a password gets an email during the request; send it in the background.
- Delete my account asks for no password, so an unattended or stolen session can erase the account.
- Sign-in link's response time can reveal an account, as the email is sent during the request.
- Sign-in link and Forgot password have no rate limit, so anyone can flood a known address with emails.
- Add a member tells a manager whether an email already has an account, and shows that user's own display name.
- Any manager can demote or remove every other manager, so one manager can take an association over.
- Any manager can send or revoke any member's sign-in link, another manager's included; revoking signs that user out of their link sessions everywhere, not only in this association.
- Send link has no rate limit, so a manager can flood a member with emails.
- Opening someone else's access link silently replaces the current session, so an attacker could get a victim working in the attacker's account.
- `POST /delete-account`, `POST /revoke-access-link`, `POST /association/new`, `POST /association/{slug}/members`, `POST /association/{slug}/members/{user_id}/role`, `POST /association/{slug}/members/{user_id}/remove`, `POST /association/{slug}/members/{user_id}/send-link` and `POST /association/{slug}/members/{user_id}/revoke-link` have no CSRF token and rely on the session cookie's SameSite setting, which is unchecked.

## Future

- Cleanup: a procedure to purge old planning data (e.g. past absences, registrations and closures), which today is kept forever.
- Cleanup: an association left with no member stays forever, unreachable, with its slug and share link; decide its fate (automatic deletion, or a superuser action).
