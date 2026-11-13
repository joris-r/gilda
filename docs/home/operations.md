# Operations

## List my associations

Cases:

- [listed] The associations the signed-in user is a member of, each
  with their role there, their upcoming and obsolete registrations,
  and its planning period, if any.
- [upcoming] The upcoming registrations are the user's registrations
  dated today or later and not obsolete, sorted by date, then start:
  - every proposed one;
  - the confirmed ones up to the later of 27 days after today and,
    when the association has a planning period, its last date.
- [obsolete] The obsolete registrations are the user's obsolete
  registrations dated today or later, sorted by date, then start.
- [period] With a planning period, the user's registration count, as
  /planning/model/registration defines it.
