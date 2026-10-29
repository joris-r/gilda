# Dev43 state

Updated on the human's decisions, and at the agent's hand-over (Step).

- Dev43: 2.0.0
- Specification: complete
- Increment: mailer-local-sendmail
- Shape: code-only
- Phase: Implementation
- Step: Production
- Stash:

## Scope of the current increment

Switch production email sending from SMTP to the local `sendmail`
binary (alwaysdata has no local SMTP listener and requires auth the
app doesn't implement). Selected implicitly: no `SMTP_HOST` set means
use `sendmail`. Development and tests keep using Mailpit over SMTP,
unmodified. No observable behavior change; existing suites pass as-is.
