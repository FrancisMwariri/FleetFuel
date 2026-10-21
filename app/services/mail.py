import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import get_settings


def send_password_reset_email(email: str, token: str) -> bool:
    settings = get_settings()
    if not all(
        [
            settings.mail_host,
            settings.mail_from,
            settings.password_reset_url,
        ]
    ):
        return False
    message = EmailMessage()
    message["Subject"] = "FleetFuel password reset"
    message["From"] = settings.mail_from
    message["To"] = email
    reset_url = f"{settings.password_reset_url.rstrip('/')}#token={quote(token)}"
    message.set_content(
        f"Use this one-time link within 30 minutes to reset your password:\n{reset_url}"
    )
    context = ssl.create_default_context()
    with smtplib.SMTP(settings.mail_host, settings.mail_port, timeout=10) as client:
        client.starttls(context=context)
        if settings.mail_username:
            client.login(settings.mail_username, settings.mail_password or "")
        client.send_message(message)
    return True
