# Email reliability

Sign-up fails cleanly when the confirmation email cannot be sent; the
Mailpit test helpers pick the latest email reliably, and the
email-verification migration passes the backend lint.

## Behavior

### API: `POST /api/accounts`

Adds:

- R10: 503 when the confirmation email cannot be sent; nothing is
  saved.

`POST /api/accounts/verify/resend` is unchanged: it still answers 204
when the email cannot be sent.

### Screens: `/signup`

Adds:

- When the confirmation email cannot be sent: "We couldn't send the
  confirmation email. Try again later."
