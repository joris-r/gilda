# Contents

The emails. Each is sent in the interface's language, as
/ui/language/emails; the English text, then the French.

## Confirmation email

Sent by Create account. Goal: have the
user confirm their email by opening the link.

- Subject: `Confirm your email`.
- One line asking to confirm by opening the link, then the link.

```
Subject: Confirm your email

Confirm your email by opening this link:

https://…/verify-email?token=…
```

```
Subject: Confirmez votre adresse e-mail

Confirmez votre adresse e-mail en ouvrant ce lien :

https://…/verify-email?token=…
```

## Password reset email

Sent by Request password reset. Goal: let the
user choose a new password, and say how long the link lasts.

- Subject: `Reset your password`.
- One line asking to choose a new password by opening the link, valid
  for one hour, then the link.

```
Subject: Reset your password

Choose a new password by opening this link, valid for one hour:

https://…/reset-password?token=…
```

```
Subject: Réinitialisez votre mot de passe

Choisissez un nouveau mot de passe en ouvrant ce lien, valable une heure :

https://…/reset-password?token=…
```

## Sign-in link email

Sent by Request access link. Goal: give the user
their lasting sign-in link, and say to keep the email.

- Subject: `Your sign-in link`.
- One line asking to sign in by opening the link, one saying to keep
  the email as the link stays valid until revoked, then the link.

```
Subject: Your sign-in link

Sign in by opening this link. Keep this email: the link stays valid
until you revoke it.

https://…/access?token=…
```

```
Subject: Votre lien de connexion

Connectez-vous en ouvrant ce lien. Conservez cet e-mail : le lien
reste valable jusqu'à ce que vous le révoquiez.

https://…/access?token=…
```
