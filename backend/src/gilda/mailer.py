import os
import smtplib
import subprocess
from email.message import EmailMessage


def send_verification_email(to_email: str, token: str) -> None:
    link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:5173')}/verify-email?token={token}"
    message = EmailMessage()
    message["Subject"] = "Confirm your email"
    message["From"] = os.environ.get("SMTP_FROM", "no-reply@gilda.example")
    message["To"] = to_email
    message.set_content(f"Confirm your email by opening this link:\n\n{link}")

    host = os.environ.get("SMTP_HOST")
    if host is None:
        subprocess.run(["/usr/sbin/sendmail", "-t"], input=message.as_bytes(), check=True)
        return

    port = int(os.environ.get("SMTP_PORT", "25"))
    with smtplib.SMTP(host, port) as smtp:
        smtp.send_message(message)
