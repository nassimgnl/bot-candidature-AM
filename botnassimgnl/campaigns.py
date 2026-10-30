"""Preparation des envois : premiers mails et relances."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from botnassimgnl import statuses
from botnassimgnl.config import Settings
from botnassimgnl.repos.emails import first_email
from botnassimgnl.repos.profile import get_profile
from botnassimgnl.repos.templates import followup_template
from botnassimgnl.repos.variables import list_variables
from botnassimgnl.templating import build_context, render, render_html

SQLITE_DATETIME = "%Y-%m-%d %H:%M:%S"


def utc_now() -> datetime:
    """Heure UTC naive, comparable a datetime('now') de SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class PreparedEmail:
    contact_id: int
    to: str
    subject: str
    body: str
    html: str
    kind: str  # "initial" ou "relance"
    attachments: tuple[Path, ...] = ()
    in_reply_to: str | None = None


@dataclass(frozen=True)
class Preparation:
    emails: list[PreparedEmail]
    skipped: list[str]


def _thread_subject(original_subject: str) -> str:
    return original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}"


def prepare_initial(conn: sqlite3.Connection, contacts: list[dict], subject: str, body: str,
                    attachments: tuple[Path, ...], force: bool) -> Preparation:
    """Premier envoi. Les contacts deja contactes sont ignores, sauf si force=True."""
    profile, custom_variables = get_profile(conn), list_variables(conn)
    emails, skipped = [], []
    for contact in contacts:
        name = f"{contact['prenom']} {contact['nom']}"
        if not contact["email"]:
            skipped.append(f"{name} : pas d'email")
            continue
        if contact["status"] == "bounce" and not force:
            skipped.append(f"{name} : adresse en bounce")
            continue
        already_contacted = contact["status"] != "non_contacte"
        if already_contacted and not force:
            skipped.append(f"{name} : deja contacte")
            continue
        context = build_context(contact, profile, custom_variables)
        thread = first_email(conn, contact["id"]) if already_contacted else None
        emails.append(PreparedEmail(
            contact_id=contact["id"],
            to=contact["email"],
            subject=render(subject, context),
            body=render(body, context),
            html=render_html(body, context),
            kind="relance" if thread else "initial",
            attachments=attachments,
            in_reply_to=thread["message_id"] if thread else None,
        ))
    return Preparation(emails, skipped)


def _cutoff(settings: Settings, now: datetime) -> str:
    return (now - timedelta(days=settings.followup_delay_days)).strftime(SQLITE_DATETIME)


def due_followups(conn: sqlite3.Connection, settings: Settings, now: datetime | None = None) -> list[dict]:
    """Contacts sans reponse depuis X jours, encore relancables."""
    rows = conn.execute(
        """SELECT * FROM contacts
           WHERE status IN ('envoye', 'relance') AND email <> ''
             AND followups_sent < ? AND last_sent_at IS NOT NULL AND last_sent_at <= ?
           ORDER BY last_sent_at""",
        (settings.followup_max, _cutoff(settings, now or utc_now())),
    ).fetchall()
    return [dict(row) for row in rows]


def expire_followups(conn: sqlite3.Connection, settings: Settings, now: datetime | None = None) -> int:
    """Passe en "Sans reponse" les contacts relances au maximum, toujours sans reponse."""
    cursor = conn.execute(
        """UPDATE contacts SET status = 'sans_reponse', updated_at = datetime('now')
           WHERE status IN ('envoye', 'relance') AND followups_sent >= ?
             AND last_sent_at IS NOT NULL AND last_sent_at <= ?""",
        (settings.followup_max, _cutoff(settings, now or utc_now())),
    )
    conn.commit()
    return cursor.rowcount


def prepare_followups(conn: sqlite3.Connection, contacts: list[dict]) -> Preparation:
    """Relances dans le fil du premier mail, avec le template de l'etape suivante."""
    profile, custom_variables = get_profile(conn), list_variables(conn)
    emails, skipped = [], []
    for contact in contacts:
        name = f"{contact['prenom']} {contact['nom']}"
        if contact["status"] not in statuses.AWAITING_REPLY or not contact["email"]:
            skipped.append(f"{name} : non relancable")
            continue
        step = contact["followups_sent"] + 1
        template = followup_template(conn, contact["lang"], step)
        if template is None:
            skipped.append(f"{name} : aucun template de relance ({contact['lang'].upper()})")
            continue
        context = build_context(contact, profile, custom_variables)
        thread = first_email(conn, contact["id"])
        subject = _thread_subject(thread["subject"]) if thread else render(template["subject"], context)
        emails.append(PreparedEmail(
            contact_id=contact["id"],
            to=contact["email"],
            subject=subject,
            body=render(template["body"], context),
            html=render_html(template["body"], context),
            kind="relance",
            in_reply_to=thread["message_id"] if thread else None,
        ))
    return Preparation(emails, skipped)
