# Backlog

## Main list

- *nothing to report*


## Datastar experiment

Rebuild, in this order; each item moves its rules out of the `api.md` pages, ports its tests, deletes its endpoints where no later item needs them, and restores its scenario once its screens are all back:

- Members: the list, "Show all", "not joined yet" and Add a member, with the form dialog (title, close button).
- Members: the edit dialog, role changes and Remove from the association; restores "A volunteer becomes manager".
- Members: Revoke link and Send link; restores "A volunteer signs in by link".
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


## Quality

- Spec: `GET /api/associations` and My associations sit in the core pages though R12–R14 are planning's; move them to a home page once other modules add their part.
- Cleanup: purge expired sessions (Advanced Alchemy's delete_expired) and expired email confirmation and password reset tokens regularly, so their tables stay small.
- API: drop `has_account` from members, which no screen uses since the access link.
- Association: refuse a name made only of spaces, at creation and on rename.
- Association: a manager can change the association's timezone (fixed to Europe/Paris for now) and set its preferred language, used for emails sent to its members by someone else (e.g. a manager); My associations then needs the timezone in `GET /api/associations`.
- Planning: with many slots in a day, the narrow-screen Schedule becomes unusable; stack a day's slots vertically in a single column. (3–4 slots a day, as at La Fabrique, work today.)
- Backend: align the preference unique constraint's name with the model's naming convention, so autogenerated migrations stop proposing to rename it.
- Quality: run Prettier and ESLint on `e2e/` in `make lint`; `scenarios.spec.ts` is not formatted today.
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
- Opening someone else's access link silently replaces the current session, so an attacker could get a victim working in the attacker's account.
- `POST /delete-account`, `POST /revoke-access-link` and `POST /association/new` have no CSRF token and rely on the session cookie's SameSite setting, which is unchecked.

## Future

- Cleanup: a procedure to purge old planning data (e.g. past absences, registrations and closures), which today is kept forever.
- Cleanup: an association left with no member stays forever, unreachable, with its slug and share link; decide its fate (automatic deletion, or a superuser action).
