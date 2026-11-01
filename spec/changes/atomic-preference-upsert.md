# atomic-preference-upsert: setting a preference is atomic

Setting a preference through `PUT /api/associations/{id}/preferences/{slot_id}/{user_id}`
succeeds even when several requests for the same member and slot run
at once.

## Technical

- Setting a preference is a single PostgreSQL
  `INSERT … ON CONFLICT (user_id, slot_id) DO UPDATE`; the last write
  wins.
