"""Envoi groupe en arriere-plan, avec pause entre deux emails et limite journaliere."""

import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Callable

from insider.campaigns import PreparedEmail
from insider.config import Settings
from insider.db import connect
from insider.mailer import MailerError, OutgoingEmail, send_email
from insider.repos.emails import record_email, sent_today

logger = logging.getLogger(__name__)

SendFunction = Callable[[Settings, OutgoingEmail, str], str]


@dataclass
class SendJob:
    id: str
    total: int
    sent: int = 0
    failed: int = 0
    status: str = "running"  # running | done | stopped | limit
    log: list[str] = field(default_factory=list)
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "total": self.total, "sent": self.sent, "failed": self.failed,
                "status": self.status, "log": self.log[-50:]}


_jobs: dict[str, SendJob] = {}
_jobs_lock = threading.Lock()


def get_job(job_id: str) -> SendJob | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def active_job() -> SendJob | None:
    with _jobs_lock:
        return next((job for job in _jobs.values() if job.status == "running"), None)


def _mark_contact(conn, item: PreparedEmail) -> None:
    if item.kind == "relance":
        conn.execute(
            """UPDATE contacts SET status = 'relance', followups_sent = followups_sent + 1,
               last_sent_at = datetime('now'), updated_at = datetime('now') WHERE id = ?""",
            (item.contact_id,),
        )
    else:
        conn.execute(
            """UPDATE contacts SET status = 'envoye', last_sent_at = datetime('now'),
               updated_at = datetime('now') WHERE id = ?""",
            (item.contact_id,),
        )
    conn.commit()


def _send_one(conn, settings: Settings, item: PreparedEmail, sender_name: str,
              send: SendFunction, job: SendJob) -> None:
    outgoing = OutgoingEmail(to=item.to, subject=item.subject, body=item.body,
                             attachments=item.attachments, in_reply_to=item.in_reply_to)
    try:
        message_id = send(settings, outgoing, sender_name)
    except (MailerError, OSError) as exc:
        logger.warning("Envoi echoue vers %s : %s", item.to, exc)
        record_email(conn, item.contact_id, item.kind, item.subject, item.body, None, ok=False, error=str(exc))
        job.failed += 1
        job.log.append(f"❌ {item.to} — {exc}")
        return
    record_email(conn, item.contact_id, item.kind, item.subject, item.body, message_id, ok=True)
    _mark_contact(conn, item)
    job.sent += 1
    job.log.append(f"✅ {item.to}")


def run_job(job: SendJob, settings: Settings, items: list[PreparedEmail], sender_name: str,
            send: SendFunction = send_email) -> None:
    conn = connect(settings.database_path)
    try:
        for index, item in enumerate(items):
            if job.cancel_event.is_set():
                job.status = "stopped"
                return
            if sent_today(conn) >= settings.daily_send_limit:
                job.status = "limit"
                job.log.append(f"⛔ Limite de {settings.daily_send_limit} emails/jour atteinte. Reprends demain.")
                return
            _send_one(conn, settings, item, sender_name, send, job)
            is_last = index == len(items) - 1
            if not is_last and job.cancel_event.wait(settings.send_delay_seconds):
                job.status = "stopped"
                return
        job.status = "done"
    except Exception:  # le thread ne doit jamais mourir silencieusement
        logger.exception("Erreur inattendue pendant l'envoi groupe")
        job.status = "stopped"
        job.log.append("⚠️ Erreur inattendue, envoi interrompu (voir le terminal).")
    finally:
        conn.close()


def start_job(settings: Settings, items: list[PreparedEmail], sender_name: str,
              send: SendFunction = send_email) -> SendJob:
    job = SendJob(id=uuid.uuid4().hex[:12], total=len(items))
    with _jobs_lock:
        _jobs[job.id] = job
    thread = threading.Thread(target=run_job, args=(job, settings, items, sender_name, send), daemon=True)
    thread.start()
    return job
