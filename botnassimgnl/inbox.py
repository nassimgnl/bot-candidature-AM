"""Lecture de la boite mail (IMAP) pour detecter reponses et bounces."""

import imaplib
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from email.parser import BytesHeaderParser
from email.utils import parseaddr

from botnassimgnl import statuses
from botnassimgnl.config import Settings
from botnassimgnl.repos.emails import earliest_sent_date, message_ids_by_contact

IMAP_TIMEOUT_SECONDS = 30
MAX_MESSAGES_SCANNED = 500
BOUNCE_SENDERS = re.compile(r"(mailer-daemon|postmaster|mail delivery)", re.IGNORECASE)
MESSAGE_ID_PATTERN = re.compile(r"<[^<>\s]+>")
HEADER_FIELDS = "(BODY.PEEK[HEADER.FIELDS (FROM IN-REPLY-TO REFERENCES SUBJECT)])"
BOUNCE_BODY = "(BODY.PEEK[TEXT]<0.20000>)"


class InboxError(RuntimeError):
    """Echec de lecture de la boite mail."""


@dataclass(frozen=True)
class InboxMessage:
    sender: str
    references: tuple[str, ...]
    body: str = ""


@dataclass(frozen=True)
class InboxReport:
    scanned: int
    replies: int
    bounces: int


def classify(messages: list[InboxMessage], contacts_by_email: dict[str, int],
             contacts_by_message_id: dict[str, int]) -> tuple[set[int], set[int]]:
    """Renvoie (ids des contacts qui ont repondu, ids des contacts en bounce)."""
    replied, bounced = set(), set()
    for message in messages:
        if BOUNCE_SENDERS.search(message.sender):
            body = message.body.lower()
            bounced.update(cid for email, cid in contacts_by_email.items() if email in body)
            continue
        sender = parseaddr(message.sender)[1].lower()
        if sender in contacts_by_email:
            replied.add(contacts_by_email[sender])
        replied.update(contacts_by_message_id[ref] for ref in message.references if ref in contacts_by_message_id)
    return replied, bounced - replied


def _fetch_messages(settings: Settings, since: datetime) -> list[InboxMessage]:
    try:
        client = imaplib.IMAP4_SSL(settings.imap_host, timeout=IMAP_TIMEOUT_SECONDS)
        client.login(settings.smtp_user, settings.smtp_password)
    except (imaplib.IMAP4.error, OSError) as exc:
        raise InboxError(f"Connexion IMAP impossible ({settings.imap_host}) : {exc}") from exc
    try:
        client.select("INBOX", readonly=True)
        _typ, data = client.search(None, "SINCE", since.strftime("%d-%b-%Y"))
        ids = data[0].split()[-MAX_MESSAGES_SCANNED:]
        messages = []
        for msg_id in ids:
            messages.append(_read_message(client, msg_id))
        return messages
    except imaplib.IMAP4.error as exc:
        raise InboxError(f"Lecture IMAP impossible : {exc}") from exc
    finally:
        try:
            client.logout()
        except (imaplib.IMAP4.error, OSError):
            pass


def _read_message(client: imaplib.IMAP4_SSL, msg_id: bytes) -> InboxMessage:
    _typ, data = client.fetch(msg_id, HEADER_FIELDS)
    raw_headers = b"".join(part[1] for part in data if isinstance(part, tuple))
    headers = BytesHeaderParser().parsebytes(raw_headers)
    sender = headers.get("From", "")
    refs = " ".join(filter(None, [headers.get("In-Reply-To", ""), headers.get("References", "")]))
    body = ""
    if BOUNCE_SENDERS.search(sender):
        _typ, body_data = client.fetch(msg_id, BOUNCE_BODY)
        body = b"".join(part[1] for part in body_data if isinstance(part, tuple)).decode("utf-8", "replace")
    return InboxMessage(sender=sender, references=tuple(MESSAGE_ID_PATTERN.findall(refs)), body=body)


def check_inbox(conn: sqlite3.Connection, settings: Settings) -> InboxReport:
    """Met a jour les statuts des contacts selon les reponses et bounces recus."""
    if not settings.imap_configured:
        raise InboxError("IMAP non configure : renseigne IMAP_HOST, SMTP_USER et SMTP_PASSWORD dans .env")
    earliest = earliest_sent_date(conn)
    if earliest is None:
        return InboxReport(scanned=0, replies=0, bounces=0)
    messages = _fetch_messages(settings, datetime.fromisoformat(earliest))
    rows = conn.execute("SELECT id, email, status FROM contacts WHERE email <> ''").fetchall()
    contacts_by_email = {row["email"].lower(): row["id"] for row in rows}
    current_status = {row["id"]: row["status"] for row in rows}
    replied, bounced = classify(messages, contacts_by_email, message_ids_by_contact(conn))

    updatable = statuses.AWAITING_REPLY | {"sans_reponse"}
    new_replies = [cid for cid in replied if current_status.get(cid) in updatable | {"bounce"}]
    new_bounces = [cid for cid in bounced if current_status.get(cid) in updatable]
    _apply(conn, new_replies, "repondu")
    _apply(conn, new_bounces, "bounce")
    return InboxReport(scanned=len(messages), replies=len(new_replies), bounces=len(new_bounces))


def _apply(conn: sqlite3.Connection, contact_ids: list[int], status: str) -> None:
    if not contact_ids:
        return
    placeholders = ",".join("?" * len(contact_ids))
    replied_sql = ", replied_at = COALESCE(replied_at, datetime('now'))" if status == "repondu" else ""
    conn.execute(
        f"UPDATE contacts SET status = ?, updated_at = datetime('now'){replied_sql} WHERE id IN ({placeholders})",
        [status, *contact_ids],
    )
    conn.commit()
