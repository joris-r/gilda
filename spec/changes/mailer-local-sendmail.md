# Mailer local sendmail

Production email sending switches from an SMTP relay to the server's
local `sendmail` binary; development and tests are unchanged.

## Technical

Replaces, in `technical.md`:

```
- Email is sent through SMTP:
  - Production: alwaysdata's SMTP relay, configured from environment
    variables.
  - Development and tests: Mailpit, run alongside PostgreSQL in
    `compose.yaml`, on non-default ports to avoid clashing with other
    projects' containers; backend and end-to-end tests query it over
    HTTP to read the sent email.
```

with:

```
- Email is sent:
  - Production: handed to the server's local `sendmail` binary.
    alwaysdata has no local SMTP listener and requires
    authentication the app does not implement, which rules out
    SMTP there.
  - Development and tests: Mailpit, run alongside PostgreSQL in
    `compose.yaml`, on non-default ports to avoid clashing with other
    projects' containers; backend and end-to-end tests query it over
    HTTP to read the sent email.
  - The two are selected by whether `SMTP_HOST` is set: set, SMTP;
    unset, `sendmail`.
```
