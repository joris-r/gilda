# Security

## Assets

- The schedule of each association: who may read it, and who may
  change it.
- The users' emails.
- The availability of the service.

## Actors

- An anonymous attacker on the internet.
- A signed-in user of another association.
- A volunteer acting beyond their role.
- A former member of an association.
- The holder of a share link it was not meant for.
- Someone with access to a user's inbox or browser.
- Someone with access to the server or its backups.

The managers of an association trust each other.

## Boundaries

- Public: the public pages and actions, for anyone, signed in or not.
- Share link: the shared schedule, for whoever holds the link.
- Signed-in: the pages and actions of a signed-in user, for any user.
- Association: the pages and actions of an association, for its
  members, as volunteer or manager.
- Inbox: the email inbox, which receives the confirmation, reset and
  access links, for whoever can read it.
- Browser: the browser of a signed-in user, for whoever can use it.
- Database: the stored data, for whoever can copy it.

## Threats

### Public

- [guess] An attacker guesses a token or a session id.
  - Mitigated: tokens and session ids too long to guess.
    - /technical/identifiers-and-security
- [enumeration] Someone who knows an email learns whether it has an
  account.
  - Accepted: signing up with the email tells whether it has an
    account with a password, and, invitation only, whether it is a
    user's; signing in and the requests for an email answer the same,
    but sooner when there is no password to check or no email to send.
- [password-guess] An attacker tries passwords against an email.
  - Accepted: as many tries as requests, without limit, against
    passwords of at least 8 characters.
- [link-swap] An attacker's access link, opened by a victim, signs the
  victim in as the attacker.
  - Accepted: the victim acts as the attacker, who sees what the victim
    enters, until the victim signs out.
- [claim-takeover] An attacker who knows the email of a member added
  by a manager, and verified, creates an account with it and signs in
  as that member.
  - Accepted: the member's account, memberships and roles included,
    for as long as the attacker uses the session; a password reset by
    the member does not end it.
- [flood] An attacker floods the public requests that send emails.
  - Accepted: one email per request, without limit: by sign-up, to an
    address without a password, only a user's or the superuser's when
    invitation only; by the other requests, to a user's address.

### Share link

- [share-forwarded] A share link reaches someone it was not meant for.
  - Mitigated: a manager revokes the link, or replaces it with a new
    one.
    - /planning/operations/revoke-share-link/revoked
    - /planning/operations/create-share-link/created
  - Accepted: the association's Schedule, as a member sees it, until
    the link is revoked or replaced.
- [flood-shared] The holder of a share link floods the requests of the
  shared schedule that build many weeks.
  - Accepted: as many requests as sent, without limit, each building
    the weeks up to the one after the planning period's end, which a
    manager sets without limit, or a little over 520 weeks for More
    weeks and the refresh on a new day.

### Signed-in

- [csrf] Another site makes a signed-in user's browser run an action.
  - Accepted: any action of the user, from a site of the same
    registrable domain only: the `session` cookie is `SameSite=Lax`,
    the framework's default.

### Association

- [other-association] A user who is not a member reads or changes an
  association, or a member reaches the data of another association
  through its ids.
  - Mitigated: every page and operation of an association, but the
    shared schedule, refuses non-members, and the ids given lead only
    to that association's data.
    - /core/ui/unknown-association/shown
    - /core/operations/general/member
    - /core/operations/general/manager
    - /core/operations/general/not-member
    - /planning/operations/general/unknown
    - /planning/operations/edit-absence/unknown
    - /planning/operations/delete-absence/unknown
- [volunteer] A volunteer runs an operation of the managers.
  - Mitigated: the managers' operations refuse volunteers, who act
    only for themselves.
    - /core/operations/general/manager
    - /planning/operations/general/other
    - /planning/operations/change-registration/forbidden
- [former-member] A removed member keeps reaching the association with
  their session or access link.
  - Mitigated: removal ends the membership, which the mitigations of
    /security/threats/other-association then refuse.
    - /core/operations/remove-member
- [injection] A user's text runs as HTML or script in another user's
  browser.
  - Mitigated: templates escape every value they show.
    - /technical/identifiers-and-security
- [flood-weeks] A member floods the requests that build many weeks.
  - Accepted: as many requests as sent, without limit, each building
    the weeks up to the one after the planning period's end, which a
    manager sets without limit, or a little over 520 weeks for More
    weeks and the refresh on a new day.
- [flood-access-links] A manager floods the access-link emails.
  - Accepted: one email per request, without limit, to the members of
    their associations.

### Inbox

- [inbox-link] Someone with access to the inbox uses a link from it.
  - Mitigated: the confirmation and reset links expire, and the access
    link can be revoked by its user or a manager.
    - /core/operations/create-account/confirmation
    - /core/operations/request-password-reset/sent
    - /core/operations/revoke-my-access-link/revoked
    - /core/operations/revoke-access-link
  - Accepted: the user's account, through the access link until it is
    revoked, and through the session that an unexpired confirmation or
    reset link opens; the reset link also sets a password, which lasts
    until the user resets it.

### Browser

- [stolen-session] Someone with access to the browser takes over its
  session, even after a password reset.
  - Accepted: the user's account, until the session is signed out,
    unused for 14 days, replaced by a sign-in in that browser, or its
    access link revoked, or the account deleted.
- [stolen-manager] A stolen manager session deletes an association
  for good.
  - Accepted: every association the user manages.

### Database

- [database-theft] An attacker copies the database.
  - Mitigated: passwords are stored hashed.
    - /technical/identifiers-and-security
  - Accepted: the password hashes, to guess offline, against Argon2
    and passwords of at least 8 characters; everything else, the
    session ids and tokens included, stored in clear: with them it
    acts as each user with a live session, access link or unexpired
    token, and reads each shared schedule.
