# UI

## Header

× - [menu] Signed in, at the right, the user's display name, opening a
×   menu with the language selector, "Revoke my sign-in link", "Delete
×   my account" and "Sign out".
- [menu] Signed in, at the right, the user's display name, opening a
  menu with the language selector, "Revoke my sign-in link" when the
  user has an AccessLink, "Delete my account" and "Sign out".

  - [revoked] it shows "Your sign-in link is revoked."; …
  - [none] /core/operations/revoke-my-access-link/none, a success: it
    shows "You have no sign-in link.";
  - [leaves] after either, "Revoke my sign-in link" leaves the menu at
    once;

## Members

- [revoke-link] "Revoke link" shows only for a member with an access …
  link; it asks "Revoke <name>'s sign-in link?" with [Revoke]; …
×   confirming runs /core/operations/revoke-access-link for the member
×   and shows
×   "<name>'s sign-in link is revoked."
  confirming runs /core/operations/revoke-access-link for the member:
  - [revoked] success: "<name>'s sign-in link is revoked.";
  - [none] /core/operations/revoke-access-link/none, a success:
    "<name> has no sign-in link.";
  - [link-leaves] after either, the member's dialog, opened again,
    has no "Revoke link".
- [rename] "Rename the association" opens the dialog "Rename the …
×   - [renamed] Another name runs /core/operations/update-association
  - [renamed] A name other than the association's current one runs
    /core/operations/update-association
    with Name alone; …
×   - [same-name] The same name closes the dialog and changes nothing.
  - [same-name] The association's current name closes the dialog and
    changes nothing.
- [change-slug] "Change the association identifier" opens the dialog …
×   - [slug-changed] Another slug runs /core/operations/update-association
  - [slug-changed] A slug other than the association's current one
    runs /core/operations/update-association
    with Association identifier alone; …
×   - [same-slug] The same slug closes the dialog and changes nothing.
  - [same-slug] The association's current slug closes the dialog and
    changes nothing.
- [delete] "Delete the association" asks "Delete <name>? Its schedule …
  and its members' registrations are erased. This cannot be undone." …
×   with a field "Type the association's name to confirm" and [Delete],
×   enabled only when the field holds exactly the association's name.
  with a field "Type the association's name to confirm" and [Delete],
  enabled only when the field holds exactly the <name> of the
  question, the name the screen shows, even when the association was
  renamed since the screen opened.
  - [delete-refused] Refused: Members shows again, as it now is. …
  - [deleted-name] The <name> of "<name> is deleted." is the
    association's name when it was deleted.

## Access link

  the token; on success, My associations shows, signed in. …
- [running] While it runs, on opening or after [Try again]: "Signing
  you in…", and nothing else under the header.
- [failed] It failing, on the server or on the way to it: the generic
  error of /ui/errors/generic, with [Try again], which runs
  /core/operations/sign-in-by-access-link again with the token.

## Confirm email

  on success, My associations shows, signed in. …
- [running] While it runs, on opening or after [Try again]:
  "Confirming your email…", and nothing else under the header.
- [failed] It failing, on the server or on the way to it: the generic
  error of /ui/errors/generic, with [Try again], which runs
  /core/operations/confirm-email again with the token.
