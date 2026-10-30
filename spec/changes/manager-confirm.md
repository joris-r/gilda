# Manager confirm

A manager can confirm a proposed registration on behalf of the
registered member.

## Behavior

### API: `PATCH /api/associations/{id}/registrations/{registration_id}`

Replaces R7:

- R7: The registered user or a manager confirms, and only a `proposed`
  registration that is not obsolete; the registered user or a manager
  cancels a registration that is not cancelled. Anyone else: 403; any
  other change: 409.

### Screens: `/associations/{id}/schedule`

In the menu on an occurrence or an obsolete registration, replaces
"the user's own proposed registration: \"Confirm\"":

- the user's own proposed registration, or any proposed one for a
  manager: "Confirm";
