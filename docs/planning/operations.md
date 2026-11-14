# Operations

## General

/core/operations/general applies.

- [member] Every operation below on an association, but Get shared
  schedule, requires a signed-in member of the association, as
  /core/operations/general/signed-out and
  /core/operations/general/unknown-association.

## Initial state

- [empty] No slot, closure, planning period, preference, absence,
  note, registration or share link.

## Add slot

Inputs:
- `weekday: one of monday, tuesday, wednesday, thursday, friday,
  saturday, sunday`
- `start: time`
- `end: time`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [order] Start not before end: refused.
- [exists] The association already has that slot: refused.
- [added] Otherwise: a slot is stored with them, with an id no slot
  has.

## Edit slot

Inputs:
- `slot: /planning/model/slot`
- `weekday: one of monday, tuesday, wednesday, thursday, friday,
  saturday, sunday`
- `start: time`
- `end: time`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [unknown] The slot is not of this association: refused.
- [order] Start not before end: refused.
- [exists] Another slot of the association has them: refused.
- [edited] Otherwise: the slot takes the weekday, start and end, and
  keeps its preferences.

## Delete slot

Inputs:
- `slot: /planning/model/slot`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [unknown] The slot is not of this association: refused.
- [deleted] Otherwise: the slot and its preferences are deleted.

## Add closure

Inputs:
- `first: date`
- `last: date`
- `label: string`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [order] Last before first: refused.
- [added] Otherwise: a closure is stored with the dates and label,
  empty or not, with an id no closure has.

## Edit closure

Inputs:
- `closure: /planning/model/closure`
- `first: date`
- `last: date`
- `label: string`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [unknown] The closure is not of this association: refused.
- [order] Last before first: refused.
- [edited] Otherwise: the closure takes the dates and label.

## Delete closure

Inputs:
- `closure: /planning/model/closure`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [unknown] The closure is not of this association: refused.
- [deleted] Otherwise: the closure is deleted.

## Set planning period

Inputs:
- `first: date`
- `last: date`

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [order] Last before first: refused.
- [set] Otherwise: the association's period has the dates, replacing
  the previous one.

## Clear planning period

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [cleared] Otherwise: the association has no period anymore.

## Set preference

Inputs:
- `user: /core/model/user`
- `slot: /planning/model/slot`
- `value: one of preferred, possible, unavailable`

Cases:
- [other] A volunteer, for another member: refused.
- [unknown] The slot is not of this association, or the user not a
  member: refused.
- [set] Otherwise: the member's preference on the slot is the value,
  replacing the previous one, even when several requests for the same
  member and slot run at once.

## Delete preference

Inputs:
- `user: /core/model/user`
- `slot: /planning/model/slot`

Cases:
- [other] A volunteer, for another member: refused.
- [unknown] The slot is not of this association, or the user not a
  member: refused.
- [deleted] Otherwise: the member has no preference on the slot
  anymore.

## Add absence

Inputs:
- `first: date`
- `last: date`

Cases:
- [order] Last before first: refused.
- [added] Otherwise: an absence is stored as the signed-in user's,
  with the dates and an id no absence has.

## Edit absence

Inputs:
- `absence: /planning/model/absence`
- `first: date`
- `last: date`

Cases:
- [unknown] The absence is not the signed-in user's in this
  association: refused.
- [order] Last before first: refused.
- [edited] Otherwise: the absence takes the dates.

## Delete absence

Inputs:
- `absence: /planning/model/absence`

Cases:
- [unknown] The absence is not the signed-in user's in this
  association: refused.
- [deleted] Otherwise: the absence is deleted.

## Set note

Inputs:
- `text: string`

Cases:
- [set] The signed-in user's note in the association is the text,
  replacing the previous one.

## Get schedule

The occurrences, obsolete registrations and closures between two
dates, both included.

Inputs:
- `first: optional date`
- `last: optional date`

Cases:
- [reversed] Both dates, last before first: refused.
- [range] Both dates: that range.
- [default] Otherwise: the range starts on the Monday of the week
  before today's and spans six weeks, and more if needed to reach the
  end of the week after the one that holds the planning period's last
  date.
- [result] In both:
  - [registration] an occurrence's registration is the one that is not
    cancelled; else the cancelled one created last; else none;
  - [closures] the closures are those that cover at least one date of
    the range;
  - [order] occurrences and obsolete registrations are sorted by date,
    then start.

## Register

Inputs:
- `user: /core/model/user`
- `date: date`
- `start: time`
- `end: time`

Cases:
- [other] A volunteer registering another member: refused.
- [non-member] The user is not a member of the association: refused.
- [past] The date is before today: refused.
- [no-occurrence] No occurrence has this date, start and end: refused.
- [taken] The occurrence already holds a registration that is not
  cancelled: refused.
- [self] A member registering themself: a registration is stored for
  them on the occurrence, `confirmed`, created now, with an id no
  registration has.
- [proposed] Otherwise, a manager registering another member: stored
  the same, `proposed`.

## Change registration

Confirms or cancels a registration.

Inputs:
- `registration: /planning/model/registration`
- `status: one of confirmed, cancelled`

Cases:
- [unknown] The registration is not of this association: refused.
- [forbidden] Signed-in user neither the registered user nor a
  manager: refused.
- [past] The registration is dated before today: refused.
- [confirm] `confirmed`, on a `proposed` registration that is not
  obsolete: it becomes `confirmed`.
- [cancel] `cancelled`, on a registration that is not cancelled: it
  becomes `cancelled`.
- [other] Any other change: refused.

## Create share link

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [created] Otherwise: a ShareLink is stored for the association,
  replacing the previous one.

## Revoke share link

Cases:
- [volunteer] Signed-in user a volunteer: refused.
- [revoked] Otherwise: the ShareLink, if any, is deleted.

## Get shared schedule

Signed in or not.

Inputs:
- `token: string`
- `first: optional date`
- `last: optional date`

Cases:
- [unknown] No ShareLink has this token: refused.
- [schedule] Otherwise: for the ShareLink's association, as
  /planning/operations/get-schedule with the dates.

## Remove member

Extends /core/operations/remove-member.

Trigger: with /core/operations/remove-member.

Cases:
- [planning] When the membership ends:
  - the member's registrations in the association dated today or
    later and not cancelled become cancelled;
  - their preferences, absences and note there are deleted;
  - their other registrations stay, with their display name.

## Delete account

Extends /core/operations/delete-account.

Trigger: with /core/operations/delete-account.

Cases:
- [planning] Each membership that ends does so as
  /planning/operations/remove-member/planning.

## Delete association

Extends /core/operations/delete-association.

Trigger: with /core/operations/delete-association.

Cases:
- [planning] Its slots, closures, planning period, preferences,
  absences, notes, share link and registrations are erased.
