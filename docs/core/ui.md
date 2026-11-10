# UI

## Access

- [signed-out] Signed out, every page but `/signup`, `/verify-email`,
  `/forgot-password`, `/reset-password`, `/sign-in-link` and `/access`
  shows Sign in.

## Header

On every page; mockup in `design/header.md`.

Shows:
- [logo] the logo, leading to `/` (not testable);
- [location] signed in, to the right of the logo, where the user is:
  - My associations: "My associations";
  - Schedule: the association's name;
  - Members, Schedule settings, My availability: the association's
    name, then the screen's name;
  - New association: "My associations", leading to `/`, then "New
    association".
- [association-link] The association's name leads to its Schedule.
- [shared] On Shared schedule, signed in or not: the association's
  name, leading nowhere, and the language selector alone at its right.
- [title] Signed in, the location stands for the screen's title;
  screens have no back link.
- [menu] Signed in, at the right, the user's display name, opening a
  menu with the language selector, "Revoke my sign-in link", "Delete
  my account" and "Sign out".
- [signed-out] Signed out, at the right, the language selector alone.

Actions:
- [language] The language selector switches between English and
  French; the choice is kept in the browser across visits and wins
  over /ui/language/default.
- [revoke] "Revoke my sign-in link" asks "Revoke your sign-in link?
  Sessions opened with it are signed out." with [Confirm]; confirming
  runs /core/operations/revoke-my-access-link:
  - [revoked] it shows "Your sign-in link is revoked.";
  - [this-session] when this session was opened with the link, it
    leads to Sign in.
- [delete] "Delete my account" asks "Delete your account? You leave
  all your associations and your upcoming registrations are cancelled.
  This cannot be undone." with [Delete my account]; confirming runs
  /core/operations/delete-account and leads to Sign in.
- [sign-out] "Sign out" runs /core/operations/sign-out and leads to
  Sign in.

## Sign in

At `/`, signed out; mockup in `design/sign-in.md`.

Shows:
- [form] Email, Password and [Sign in]; then "Forgot your password?"
  and "Sign in with an email link"; then "No account yet? Create an
  account".

Actions:
- [sign-in] [Sign in] runs /core/operations/sign-in:
  - [signed-in] success: My associations shows;
  - [wrong] /core/operations/sign-in/wrong: "Wrong email or password."
    under the form.
- [create] "Create an account" leads to `/signup`.
- [forgot] "Forgot your password?" leads to `/forgot-password`.
- [link] "Sign in with an email link" leads to `/sign-in-link`.

## Sign-in link

At `/sign-in-link`; mockup in `design/sign-in-link.md`.

Shows:
- [form] Email and [Send me a link]; then "Back to Sign in", leading to
  Sign in.

Actions:
- [send] [Send me a link] runs /core/operations/request-access-link,
  then shows "If <email> is known here, a sign-in link has been sent
  to it." instead of the form.

## Access link

At `/access?token=<token>`, opened from the access link.

- [signed-in] It runs /core/operations/sign-in-by-access-link with
  the token; on success, My associations shows, signed in.
- [invalid] /core/operations/sign-in-by-access-link/invalid: "This
  link is no longer valid.", with a way to `/sign-in-link` to request
  a new one.

## Forgot password

At `/forgot-password`; mockup in `design/forgot-password.md`.

Shows:
- [form] Email and [Send a reset link]; then "Back to Sign in".

Actions:
- [send] [Send a reset link] runs
  /core/operations/request-password-reset, then shows "If <email> has
  an account, a reset link has been sent to it." instead of the form.

## Reset password

At `/reset-password?token=<token>`, opened from the reset link;
mockup in `design/reset-password.md`.

Shows:
- [form] New password and [Set password].

Actions:
- [set] [Set password] runs /core/operations/reset-password with the
  token:
  - [reset] success: My associations shows, signed in;
  - [invalid] /core/operations/reset-password/invalid: "This link is
    no longer valid.", with a way to `/forgot-password` to request a
    new one.

## Create an account

At `/signup`; mockup in `design/create-an-account.md`.

Shows:
- [form] Display name, Email, Password and [Create account]; then
  "Already have an account? Sign in".

Actions:
- [create] [Create account] runs /core/operations/create-account:
  - [check-email] success: "Check <email> for a confirmation link."
    instead of the form, not signed in, with "Resend the email" below
    it;
  - [exists] /core/operations/create-account/exists: "An account
    already exists for this email. Sign in instead.";
  - [not-invited] /core/operations/create-account/not-invited: "This
    email has not been invited. Ask a manager of your association to
    add you as a member.";
  - [not-sent] /core/operations/create-account/not-sent: "We couldn't
    send the confirmation email. Try again later."
- [resend] "Resend the email" runs
  /core/operations/resend-confirmation and shows "Email sent."

## Confirm email

At `/verify-email?token=<token>`, opened from the confirmation link.

- [confirmed] It runs /core/operations/confirm-email with the token;
  on success, My associations shows, signed in.
- [invalid] /core/operations/confirm-email/invalid: "This link is no
  longer valid.", with a way back to `/signup` to request a new one.

## New association

At `/association/new`; mockup in `design/new-association.md`.

Shows:
- [form] Name, Association identifier (the slug, after
  `/association/`), [Create association] and Cancel.
- [follows] Until the user edits Association identifier, it holds the
  slug derived from Name, as /core/model/association/derived.
- [enabled] [Create association] is enabled only when both fields are
  not empty.

Actions:
- [create] [Create association] runs /core/operations/create-association:
  - [created] success: the new association's Schedule shows;
  - [malformed] /core/operations/create-association/malformed-slug:
    "Use only lowercase letters, digits and hyphens, starting and
    ending with a letter or a digit.";
  - [taken] /core/operations/create-association/taken: "This
    association identifier is already taken."
- [cancel] Cancel leads to My associations.

## Members

At `/association/<slug>/members`; mockups in `design/members.md`.

Shows:
- [list] the members, managers first, then by display name; each with
  their display name, email and role.
- [not-joined] A member whose email is not confirmed shows "not joined
  yet".
- [first-five] With more than 5 members, the first 5 show, then "Show
  all <n> members", which shows the others; with 5 or fewer, all show,
  without the link.
- [manager] To a manager: "+ Add a member", an edit icon "Edit
  <name>" on each member, then "Rename the association", "Change the
  association identifier" and "Delete the association".
- [volunteer] To a volunteer: the members and their roles, without
  "Add a member", the edit icons, "Rename the association", "Change
  the association identifier" and "Delete the association".

Actions:
- [add] "Add a member" opens the dialog "Add a member": Display name,
  Email, Role (Volunteer by default), [Add member]. It runs
  /core/operations/add-member:
  - [added] success: "<name> added.";
  - [already] /core/operations/add-member/already: "<name> is already
    a member."
- [edit] The edit icon opens the dialog titled with the member's
  display name: their email; Role and [Save]; under "SIGN-IN LINK",
  [Send link] and "Revoke link"; then "Remove from the association".
- [save] [Save] with another role runs /core/operations/change-role:
  - [changed] success: "<name> is now <role>.";
  - [last-manager] /core/operations/change-role/last-manager: "An
    association keeps at least one manager."
- [same-role] [Save] with the same role closes the dialog and changes
  nothing.
- [revoke-link] "Revoke link" shows only for a member with an access
  link; it asks "Revoke <name>'s sign-in link?" with [Revoke];
  confirming runs /core/operations/revoke-access-link and shows
  "<name>'s sign-in link is revoked."
- [send-link] "Send link" asks "Send <name>'s sign-in link by email?"
  with [Send]; confirming runs /core/operations/send-access-link:
  - [sent] success: "<name>'s sign-in link is sent.";
  - [not-sent] /core/operations/send-access-link/not-sent: "We
    couldn't send <name>'s sign-in link. Try again later."
- [remove] "Remove from the association" asks "Remove <name> from the
  association? Their upcoming registrations are cancelled." with
  [Remove]; confirming runs /core/operations/remove-member:
  - [removed] success: "<name> is removed.";
  - [remove-last-manager] /core/operations/remove-member/last-manager: "An
    association keeps at least one manager.";
  - [themself] a manager who removes themself is led to My
    associations.
- [rename] "Rename the association" opens the dialog "Rename the
  association": Name, filled with the name, and [Save], enabled only
  when Name is not empty.
  - [renamed] Another name runs /core/operations/update-association;
    on success, the header shows the new name, and "The association is
    now <name>."
  - [same-name] The same name closes the dialog and changes nothing.
- [change-slug] "Change the association identifier" opens the dialog
  "Change the association identifier": Association identifier, filled
  with the slug, and [Save], enabled only when it is not empty.
  - [slug-changed] Another slug runs /core/operations/update-association;
    on success, the screen moves to the new URL and shows "The
    association identifier is now <slug>."
  - [same-slug] The same slug closes the dialog and changes nothing.
  - [refused] A malformed or taken slug shows the message of
    /core/ui/new-association/malformed or
    /core/ui/new-association/taken.
- [delete] "Delete the association" asks "Delete <name>? Its schedule
  and its members' registrations are erased. This cannot be undone."
  with a field "Type the association's name to confirm" and [Delete],
  enabled only when the field holds exactly the association's name.
  Confirming runs /core/operations/delete-association, leads to My
  associations and shows "<name> is deleted."

## Unknown association

- [shown] A screen of an association whose slug is unknown, or of
  which the user is not a member, shows "This association does not
  exist or you are not a member." with a way to My associations.
