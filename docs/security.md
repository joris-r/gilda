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

The managers of an association trust each other.

## Boundaries

- The public pages and actions: anyone, signed in or not.
- A share link: whoever holds it.
- The pages and actions of a signed-in user: any user.
- The pages and actions of an association: its members, as volunteer
  or manager.
- The email inbox, which receives the confirmation, reset and access
  links: whoever can read it.

## Threats

- [other-association] A user who is not a member reads or changes an
  association, or a member reaches the data of another association
  through its ids: mitigated by /core/ui/unknown-association/shown,
  the `[manager]` cases of /security/threats/volunteer, and:
  - the `[member]` cases: /planning/operations/set-preference/member,
    /planning/operations/delete-preference/member,
    /planning/operations/add-absence/member,
    /planning/operations/edit-absence/member,
    /planning/operations/delete-absence/member,
    /planning/operations/set-note/member,
    /planning/operations/get-schedule/member,
    /planning/operations/register/member,
    /planning/operations/change-registration/member;
  - the cases refusing an id of another association:
    /planning/operations/edit-slot/unknown,
    /planning/operations/delete-slot/unknown,
    /planning/operations/edit-closure/unknown,
    /planning/operations/delete-closure/unknown,
    /planning/operations/set-preference/unknown,
    /planning/operations/delete-preference/unknown,
    /planning/operations/edit-absence/unknown,
    /planning/operations/delete-absence/unknown,
    /planning/operations/register/non-member,
    /planning/operations/change-registration/unknown,
    /core/operations/change-role/not-member,
    /core/operations/remove-member/not-member,
    /core/operations/send-access-link/not-member,
    /core/operations/revoke-access-link/not-member.
- [volunteer] A volunteer runs an operation of the managers: mitigated
  by /planning/operations/set-preference/other,
  /planning/operations/delete-preference/other,
  /planning/operations/register/other,
  /planning/operations/change-registration/forbidden, and the
  `[manager]` cases:
  - /core/operations/update-association/manager,
    /core/operations/delete-association/manager,
    /core/operations/add-member/manager,
    /core/operations/change-role/manager,
    /core/operations/remove-member/manager,
    /core/operations/send-access-link/manager,
    /core/operations/revoke-access-link/manager;
  - /planning/operations/add-slot/manager,
    /planning/operations/edit-slot/manager,
    /planning/operations/delete-slot/manager,
    /planning/operations/add-closure/manager,
    /planning/operations/edit-closure/manager,
    /planning/operations/delete-closure/manager,
    /planning/operations/set-planning-period/manager,
    /planning/operations/clear-planning-period/manager,
    /planning/operations/create-share-link/manager,
    /planning/operations/revoke-share-link/manager.
- [former-member] A removed member keeps reaching the association with
  their session or access link: mitigated by
  /core/operations/remove-member, after which the cases of
  /security/threats/other-association refuse them.
- [guess] An attacker guesses a token or a session id: mitigated by
  /technical/identifiers-and-security.
- [share-forwarded] A share link reaches someone it was not meant for:
  mitigated by /planning/operations/revoke-share-link/revoked and
  /planning/operations/create-share-link/created; the exposure until
  then is accepted.
- [enumeration] Someone who knows an email learns whether it has an
  account: accepted.
- [password-guess] An attacker tries passwords against an email:
  accepted.
- [database-theft] An attacker copies the database: the passwords are
  mitigated by /technical/identifiers-and-security; the rest is
  accepted.
- [inbox-link] Someone with access to the inbox uses a link from it:
  mitigated by /core/operations/create-account/confirmation and
  /core/operations/request-password-reset/sent, whose links expire,
  and by /core/operations/revoke-my-access-link/revoked
  and /core/operations/revoke-access-link; the exposure of an access
  link until then is accepted.
- [stolen-session] Someone with access to the browser takes over its
  session, even after a password reset: accepted.
- [link-swap] An attacker's access link, opened by a victim, signs the
  victim in as the attacker: accepted.
- [stolen-manager] A stolen manager session deletes an association
  for good: accepted.
- [claim-takeover] An attacker who knows the email of a member added
  by a manager, and verified, creates an account with it and signs in
  as that member: accepted.
- [injection] A user's text runs as HTML or script in another user's
  browser: mitigated by /technical/identifiers-and-security.
- [csrf] Another site makes a signed-in user's browser run an action:
  accepted.
- [flood] An attacker floods the requests that build many weeks or
  that send emails: accepted.
