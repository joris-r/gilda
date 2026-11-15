# Operations

## Request access link

  - [answer] It succeeds also when the email cannot be sent. …
  - [unsent] When the email cannot be sent, a user who had no
    AccessLink still has none.

## Revoke my access link

Cases:
× - [revoked] The user's AccessLink, if any, is deleted, with the
×   sessions it opened.
- [revoked] The user has an AccessLink: it is deleted, with the
  sessions it opened.
- [none] The user has no AccessLink: nothing changes; returns that
  there was none.

## Revoke access link

× - [revoked] After no refusal: the member's AccessLink is revoked, as
×   /core/operations/revoke-my-access-link/revoked, in every association
×   they belong to, also when they have none.
- [revoked] After no refusal, the member having an AccessLink: it is
  revoked, as /core/operations/revoke-my-access-link/revoked, in every
  association they belong to.
- [none] After no refusal, the member having no AccessLink: nothing
  changes; returns that there was none.
