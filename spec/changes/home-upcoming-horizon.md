# Home upcoming horizon

My associations lists confirmed registrations up to the later of the
planning period's last date and 27 days after today.

## GET /api/associations

Replaces R12:

- R12: `upcoming` holds the user's registrations dated today or later,
  sorted by date, then start:
  - every proposed one;
  - the confirmed ones up to the later of 27 days after today and, when
    the association has a planning period, its last date.
