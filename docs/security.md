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
  - Mitigated: /technical/identifiers-and-security.
- [enumeration] Someone who knows an email learns whether it has an
  account.
  - Accepted.
- [password-guess] An attacker tries passwords against an email.
  - Accepted.
- [link-swap] An attacker's access link, opened by a victim, signs the
  victim in as the attacker.
  - Accepted.
- [claim-takeover] An attacker who knows the email of a member added
  by a manager, and verified, creates an account with it and signs in
  as that member.
  - Accepted.
- [flood] An attacker floods the public requests that send emails.
  - Accepted.

### Share link

- [share-forwarded] A share link reaches someone it was not meant for.
  - Mitigated: /planning/operations/revoke-share-link/revoked,
    /planning/operations/create-share-link/created.
  - Accepted: the exposure until it is revoked.
- [flood-shared] The holder of a share link floods the requests of the
  shared schedule that build many weeks.
  - Accepted.

### Signed-in

- [csrf] Another site makes a signed-in user's browser run an action.
  - Accepted.

### Association

- [other-association] A user who is not a member reads or changes an
  association, or a member reaches the data of another association
  through its ids.
  - Mitigated: /core/ui/unknown-association/shown,
    /core/operations/general/member,
    /core/operations/general/manager,
    /core/operations/general/not-member, and the cases refusing an id
    of another association:
    /planning/operations/edit-slot/unknown,
    /planning/operations/delete-slot/unknown,
    /planning/operations/edit-closure/unknown,
    /planning/operations/delete-closure/unknown,
    /planning/operations/set-preference/unknown,
    /planning/operations/delete-preference/unknown,
    /planning/operations/edit-absence/unknown,
    /planning/operations/delete-absence/unknown,
    /planning/operations/change-registration/unknown.
- [volunteer] A volunteer runs an operation of the managers.
  - Mitigated: /core/operations/general/manager,
    /planning/operations/set-preference/other,
    /planning/operations/delete-preference/other,
    /planning/operations/register/other,
    /planning/operations/change-registration/forbidden.
- [former-member] A removed member keeps reaching the association with
  their session or access link.
  - Mitigated: /core/operations/remove-member, after which the
    mitigations of /security/threats/other-association refuse them.
- [injection] A user's text runs as HTML or script in another user's
  browser.
  - Mitigated: /technical/identifiers-and-security.
- [flood-weeks] A member floods the requests that build many weeks.
  - Accepted.
- [flood-access-links] A manager floods the access-link emails.
  - Accepted.

### Inbox

- [inbox-link] Someone with access to the inbox uses a link from it.
  - Mitigated: /core/operations/create-account/confirmation and
    /core/operations/request-password-reset/sent, whose links expire,
    /core/operations/revoke-my-access-link/revoked,
    /core/operations/revoke-access-link.
  - Accepted: the exposure of an access link until it is revoked.

### Browser

- [stolen-session] Someone with access to the browser takes over its
  session, even after a password reset.
  - Accepted.
- [stolen-manager] A stolen manager session deletes an association
  for good.
  - Accepted.

### Database

- [database-theft] An attacker copies the database.
  - Mitigated: /technical/identifiers-and-security, for the passwords.
  - Accepted: the rest.
