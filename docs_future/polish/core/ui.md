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
