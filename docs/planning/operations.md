# Operations

## General

/core/operations/general applies.

## Initial state

- [empty] No slot, closure, planning period, preference, absence,
  note, registration or share link.

## Add slot

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `weekday: one of monday, tuesday, wednesday, thursday, friday,
  saturday, sunday`
- `start: time`
- `end: time`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [order] Start not before end: refused.
3. [exists] The association already has that slot: refused.

Then:
- [added] After no refusal: a slot is stored with them, with an id no
  slot has.

## Edit slot

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `slot: /planning/model/slot`
- `weekday: one of monday, tuesday, wednesday, thursday, friday,
  saturday, sunday`
- `start: time`
- `end: time`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [unknown] The slot is not of this association: refused.
3. [order] Start not before end: refused.
4. [exists] Another slot of the association has them: refused.

Then:
- [edited] After no refusal: the slot takes the weekday, start and
  end, and keeps its preferences.

## Delete slot

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `slot: /planning/model/slot`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [unknown] The slot is not of this association: refused.

Then:
- [deleted] After no refusal: the slot and its preferences are
  deleted.

## Add closure

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `first: date`
- `last: date`
- `label: string`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [order] Last before first: refused.

Then:
- [added] After no refusal: a closure is stored with the dates and
  label, empty or not, with an id no closure has.

## Edit closure

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `closure: /planning/model/closure`
- `first: date`
- `last: date`
- `label: string`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [unknown] The closure is not of this association: refused.
3. [order] Last before first: refused.

Then:
- [edited] After no refusal: the closure takes the dates and label.

## Delete closure

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `closure: /planning/model/closure`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [unknown] The closure is not of this association: refused.

Then:
- [deleted] After no refusal: the closure is deleted.

## Set planning period

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `first: date`
- `last: date`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [order] Last before first: refused.

Then:
- [set] After no refusal: the association's period has the dates,
  replacing the previous one.

## Clear planning period

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [cleared] Otherwise: the association has no period anymore.

## Set preference

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `member: /core/model/user`
- `slot: /planning/model/slot`
- `value: one of preferred, possible, unavailable`

Cases:
1. [member] The user is not a member of the association: refused.
2. [other] The user is a volunteer and the member is not the user:
   refused.
3. [unknown] The slot is not of this association, or the member not a
   member of the association: refused.

Then:
- [set] After no refusal: the member's preference on the slot is the
  value, replacing the previous one, even when several requests for
  the same member and slot run at once.

## Delete preference

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `member: /core/model/user`
- `slot: /planning/model/slot`

Cases:
1. [member] The user is not a member of the association: refused.
2. [other] The user is a volunteer and the member is not the user:
   refused.
3. [unknown] The slot is not of this association, or the member not a
   member of the association: refused.

Then:
- [deleted] After no refusal: the member has no preference on the slot
  anymore.

## Add absence

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `first: date`
- `last: date`

Cases:
1. [member] The user is not a member of the association: refused.
2. [order] Last before first: refused.
3. [past] Last before today: refused.
4. [overlap] One of the user's absences in this association covers a
   date from first to last that is today or later: refused.

Then:
- [added] After no refusal: an absence is stored as the user's, with
  the dates and an id no absence has.

## Edit absence

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `absence: /planning/model/absence`
- `first: date`
- `last: date`

Cases:
1. [member] The user is not a member of the association: refused.
2. [unknown] The absence is not the user's in this association:
   refused.
3. [order] Last before first: refused.
4. [past] Last before today: refused.
5. [overlap] Another of the user's absences in this association
   covers a date from first to last that is today or later: refused.

Then:
- [edited] After no refusal: the absence takes the dates.

## Delete absence

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `absence: /planning/model/absence`

Cases:
1. [member] The user is not a member of the association: refused.
2. [unknown] The absence is not the user's in this association:
   refused.

Then:
- [deleted] After no refusal: the absence is deleted.

## Set note

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `text: string`

Cases:
1. [member] The user is not a member of the association: refused.
2. [set] Otherwise: the user's note in the association is the text,
   replacing the previous one.

## Get schedule

The occurrences, obsolete registrations and closures between two
dates, both included.

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `first: optional date`
- `last: optional date`

Cases:
1. [member] The user is not a member of the association: refused.
2. [reversed] Both dates, last before first: refused.
3. [range] Both dates: that range.
4. [default] Otherwise: the range starts on the Monday of the week
   before today's and spans six weeks, and more if needed to reach the
   end of the week after the one that holds the planning period's last
   date.

Then:
- [result] After /planning/operations/get-schedule/range or
  /planning/operations/get-schedule/default:
  - [registration] an occurrence's registration is the one that is not
    cancelled; else the cancelled one created last; else none;
  - [closures] the closures are those that cover at least one date of
    the range;
  - [order] occurrences and obsolete registrations are sorted by date,
    then start.

## Register

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `member: /core/model/user`
- `date: date`
- `start: time`
- `end: time`

Cases:
1. [member] The user is not a member of the association: refused.
2. [other] The user is a volunteer and the member is not the user:
   refused.
3. [non-member] The member is not a member of the association:
   refused.
4. [past] The date is before today: refused.
5. [no-occurrence] No occurrence has this date, start and end: refused.
6. [taken] The occurrence already holds a registration that is not
   cancelled: refused.
7. [self] The member is the user: a registration is stored for them on
   the occurrence, `confirmed`, created now, with an id no
   registration has.
8. [proposed] Otherwise, the user being a manager: stored the same,
   `proposed`.

## Change registration

Confirms or cancels a registration.

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`
- `registration: /planning/model/registration`
- `status: one of confirmed, cancelled`

Cases:
1. [member] The user is not a member of the association: refused.
2. [unknown] The registration is not of this association: refused.
3. [forbidden] The user is neither the registered user nor a manager:
   refused.
4. [past] The registration is dated before today: refused.
5. [confirm] `confirmed`, on a `proposed` registration that is not
   obsolete: it becomes `confirmed`.
6. [cancel] `cancelled`, on a registration that is not cancelled: it
   becomes `cancelled`.
7. [other] Any other change: refused.

## Create share link

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [created] Otherwise: a ShareLink is stored for the association,
   replacing the previous one.

## Revoke share link

Inputs:
- `user: /core/model/user`
- `association: /core/model/association`

Cases:
1. [manager] The user is not a manager of the association: refused.
2. [revoked] Otherwise: the association's ShareLink, if any, is
   deleted.

## Get shared schedule

Inputs:
- `token: string`
- `first: optional date`
- `last: optional date`

Cases:
- [unknown] No ShareLink has this token: refused.

Then:
- [schedule] After no refusal: for the ShareLink's association, as
  /planning/operations/get-schedule with the dates, without
  /planning/operations/get-schedule/member.

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
