"""Envoi des emails par SMTP (Gmail, Outlook, Yahoo...)."""

import mimetypes
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

from botnassimgnl.config import Settings

SMTP_TIMEOUT_SECONDS = 30
SSL_PORT = 465


class MailerError(RuntimeError):
    """Echec de connexion ou d'envoi SMTP."""


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    body: str
    attachments: tuple[Path, ...] = ()
    in_reply_to: str | None = None
    references: tuple[str, ...] = field(default_factory=tuple)


def build_message(settings: Settings, email: OutgoingEmail, sender_name: str = "") -> EmailMessage:
    message = EmailMessage()
    message["From"] = formataddr((sender_name or settings.sender_name, settings.smtp_user))
    message["To"] = email.to
    message["Subject"] = email.subject
    domain = settings.smtp_user.split("@")[-1] if "@" in settings.smtp_user else None
    message["Message-ID"] = make_msgid(domain=domain)
    if email.in_reply_to:
        message["In-Reply-To"] = email.in_reply_to
        message["References"] = " ".join(email.references or (email.in_reply_to,))
    message.set_content(email.body)
    for path in email.attachments:
        mime_type, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
        message.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    return message


def _open_connection(settings: Settings) -> smtplib.SMTP:
    if not settings.smtp_configured:
        raise MailerError("SMTP non configure : renseigne SMTP_USER et SMTP_PASSWORD dans le fichier .env")
    context = ssl.create_default_context()
    try:
        if settings.smtp_port == SSL_PORT:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port,
                                      timeout=SMTP_TIMEOUT_SECONDS, context=context)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT_SECONDS)
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
        server.login(settings.smtp_user, settings.smtp_password)
    except smtplib.SMTPAuthenticationError as exc:
        raise MailerError("Identifiants refuses. Utilise un mot de passe d'application (pas ton mot de passe habituel).") from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise MailerError(f"Connexion SMTP impossible ({settings.smtp_host}:{settings.smtp_port}) : {exc}") from exc
    return server


def test_connection(settings: Settings) -> None:
    """Leve MailerError si la connexion SMTP echoue."""
    server = _open_connection(settings)
    server.quit()


def send_email(settings: Settings, email: OutgoingEmail, sender_name: str = "") -> str:
    """Envoie un email et renvoie son Message-ID."""
    message = build_message(settings, email, sender_name)
    server = _open_connection(settings)
    try:
        server.send_message(message)
    except smtplib.SMTPRecipientsRefused as exc:
        raise MailerError(f"Adresse refusee par le serveur : {email.to}") from exc
    except smtplib.SMTPException as exc:
        raise MailerError(f"Echec d'envoi a {email.to} : {exc}") from exc
    finally:
        try:
            server.quit()
        except smtplib.SMTPException:
            pass
    return message["Message-ID"]
