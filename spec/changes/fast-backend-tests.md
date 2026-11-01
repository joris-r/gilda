# fast-backend-tests: a faster backend test suite

The backend tests run in parallel and hash passwords cheaply.

## Technical

Modifies the Backend item of the test and quality policy in
`technical.md`; its new version:

- Backend: pytest, through Litestar's test client, against a real
  PostgreSQL given by `DATABASE_URL`; never SQLite or a mocked
  database.
  - Tests run in parallel with pytest-xdist, one worker per CPU; each
    test sees only the data it creates.
  - Tests hash passwords with Argon2 at its minimal cost parameters.
