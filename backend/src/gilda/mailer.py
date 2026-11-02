import os
import smtplib
import subprocess
from email.message import EmailMessage
from typing import Literal


class EmailNotSentError(Exception):
    """The email could not be handed to the mail server."""


Language = Literal["en", "fr"]

_VERIFICATION_TEXTS: dict[Language, tuple[str, str]] = {
    "en": ("Confirm your email", "Confirm your email by opening this link:"),
    "fr": ("Confirmez votre adresse e-mail", "Confirmez votre adresse e-mail en ouvrant ce lien :"),
}


def preferred_language(accept_language: str | None) -> Language:
    """French when the Accept-Language header prefers it over English, English otherwise."""
    weights: dict[str, float] = {}
    for item in (accept_language or "").split(","):
        tag, _, parameters = item.partition(";")
        code = tag.strip().lower().split("-")[0]
        quality = 1.0
        for parameter in parameters.split(";"):
            name, _, value = parameter.partition("=")
            if name.strip() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        if code in ("en", "fr"):
            weights[code] = max(weights.get(code, 0.0), quality)
    return "fr" if weights.get("fr", 0.0) > weights.get("en", 0.0) else "en"


def send_verification_email(to_email: str, token: str, language: Language) -> None:
    link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:5173')}/verify-email?token={token}"
    subject, text = _VERIFICATION_TEXTS[language]
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.environ.get("SMTP_FROM", "no-reply@gilda.example")
    message["To"] = to_email
    message.set_content(f"{text}\n\n{link}")

    try:
        _send(message)
    except (OSError, subprocess.CalledProcessError) as error:
        raise EmailNotSentError(f"Could not send an email to {to_email}.") from error


def _send(message: EmailMessage) -> None:
    host = os.environ.get("SMTP_HOST")
    if host is None:
        subprocess.run(["/usr/sbin/sendmail", "-t"], input=message.as_bytes(), check=True)
        return

    port = int(os.environ.get("SMTP_PORT", "25"))
    with smtplib.SMTP(host, port) as smtp:
        smtp.send_message(message)
