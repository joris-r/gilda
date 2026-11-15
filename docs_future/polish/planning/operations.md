# Operations

## Add closure

2. [order] Last before first: refused. …
3. [past] Last before today: refused.

## Edit closure

3. [order] Last before first: refused. …
4. [past] Last before today: refused.

## Add absence

2. [order] Last before first: refused. …
3. [past] Last before today: refused.
4. [overlap] One of the user's absences in this association covers a
   date from first to last that is today or later: refused.

## Edit absence

3. [order] Last before first: refused. …
4. [past] Last before today: refused.
5. [overlap] Another of the user's absences in this association
   covers a date from first to last that is today or later: refused.

## Set note

× 2. [set] Otherwise: the user's note in the association is the text,
×    replacing the previous one.
2. [set] Otherwise: the user's note in the association is the text
   without its leading and trailing spaces, tabs and line breaks,
   replacing the previous one.

## Get schedule

× The occurrences, obsolete registrations and closures between two
× dates, both included.
The occurrences, obsolete registrations, closures and closed days
between two dates, both included.
  - [closures] the closures are those that cover at least one date of …
    the range; …
  - [closed-days] the closed days are the dates of the range that a
    closure covers and that fall on the weekday of a slot;

## Register

- `end: time` …
- `replacing: optional /planning/model/registration`, the registration
  it replaces.

× 2. [other] The user is a volunteer and the member is not the user:
×    refused.
2. [other] The user is a volunteer, and the member is not the user or
   `replacing` is given: refused.
× 6. [taken] The occurrence already holds a registration that is not
×    cancelled: refused.
6. [taken] The occurrence already holds a registration that is not
   cancelled, unless that registration is `replacing` and its user is
   not the member: refused.
   `proposed`. …

Then:
- [replaced] After /planning/operations/register/self or
  /planning/operations/register/proposed: the occurrence's registration
  that was not cancelled before, if any, becomes `cancelled`.
