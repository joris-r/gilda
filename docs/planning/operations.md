# Operations

## General

/core/operations/general applies.

- [member] Every operation below but Get shared schedule requires a
  signed-in member of the association, as
  /core/operations/general/signed-out and
  /core/operations/general/unknown-association.

## Add slot

- [added] A new slot: it is stored.
- [exists] The association already has that slot: refused.
- [order] Start not before end: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Edit slot

- [edited] The slot takes the weekday, start and end, and keeps its
  preferences.
- [exists] Another slot of the association has them: refused.
- [order] Start not before end: refused.
- [unknown] The slot is not of this association: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Delete slot

- [deleted] The slot and its preferences are deleted.
- [unknown] The slot is not of this association: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Add closure

- [added] The closure is stored, with its dates and label.
- [no-label] The label may be empty.
- [order] Last before first: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Edit closure

- [edited] The closure takes the dates and label.
- [order] Last before first: refused.
- [unknown] The closure is not of this association: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Delete closure

- [deleted] The closure is deleted.
- [unknown] The closure is not of this association: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Set planning period

- [set] The period is set, replacing the previous one.
- [order] Last before first: refused.
- [volunteer] Signed-in user a volunteer: refused.

## Clear planning period

- [cleared] There is no period anymore.
- [volunteer] Signed-in user a volunteer: refused.

## Set preference

- [set] The member's preference on the slot is the value, replacing
  the previous one, even when several requests for the same member
  and slot run at once.
- [other] A volunteer, for another member: refused.
- [unknown] The slot is not of this association, or the user not a
  member: refused.

## Delete preference

- [deleted] The member has no preference on the slot anymore.
- [other] A volunteer, for another member: refused.
- [unknown] The slot is not of this association, or the user not a
  member: refused.

## Add absence

- [added] The absence is stored as the user's.
- [order] Last before first: refused.

## Edit absence

- [edited] The absence takes the dates.
- [order] Last before first: refused.
- [unknown] The absence is not the user's in this association:
  refused.

## Delete absence

- [deleted] The absence is deleted.
- [unknown] The absence is not the user's in this association:
  refused.

## Set note

- [set] The user's note is the text, replacing the previous one.

## Get schedule

The occurrences, obsolete registrations and closures between two
dates, both included.

- [default] The first range starts on the Monday of the week before
  today's and spans six weeks, and more if needed to reach the end of
  the week after the one that holds the planning period's last date.
- [registration] An occurrence's registration is the one that is not
  cancelled; else the latest cancelled one; else none.
- [closures] The closures are those that cover at least one date of
  the range.
- [order] Occurrences and obsolete registrations are sorted by date,
  then start.

## Register

- [self] A member registering themself: the registration is stored,
  `confirmed`.
- [proposed] A manager registering another member: the registration
  is stored, `proposed`.
- [other] A volunteer registering another member: refused.
- [no-occurrence] No occurrence has this date, start and end: refused.
- [taken] The occurrence already holds a registration that is not
  cancelled: refused.
- [non-member] The user is not a member of the association: refused.
- [past] The date is before today: refused.

## Change registration

Confirms or cancels a registration.

- [confirm] The registered user or a manager, confirming a `proposed`
  registration that is not obsolete: it becomes `confirmed`.
- [cancel] The registered user or a manager, cancelling a registration
  that is not cancelled: it becomes `cancelled`.
- [forbidden] Anyone else: refused.
- [other] Any other change: refused.
- [unknown] The registration is not of this association: refused.

## Create share link

- [created] A ShareLink is created, replacing the previous one.
- [volunteer] Signed-in user a volunteer: refused.

## Revoke share link

- [revoked] The ShareLink, if any, is deleted.
- [volunteer] Signed-in user a volunteer: refused.

## Get shared schedule

Signed in or not.

- [schedule] For the ShareLink's association, as
  /planning/operations/get-schedule.
- [unknown] No ShareLink has this token: refused.

## Remove member

Extends /core/operations/remove-member.

- [planning] When the membership ends:
  - the member's registrations in the association dated today or
    later and not cancelled become cancelled;
  - their preferences, absences and note there are deleted;
  - their other registrations stay, with their display name.

## Delete account

Extends /core/operations/delete-account.

- [planning] Each membership that ends does so as
  /planning/operations/remove-member/planning.

## Delete association

Extends /core/operations/delete-association.

- [planning] Its slots, closures, planning period, preferences,
  absences, notes, share link and registrations are erased.
