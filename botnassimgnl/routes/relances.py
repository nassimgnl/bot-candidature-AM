from flask import Blueprint, flash, redirect, render_template, url_for

from botnassimgnl.campaigns import due_followups, expire_followups, prepare_followups
from botnassimgnl.db import get_db
from botnassimgnl.repos.contacts import get_contacts
from botnassimgnl.repos.profile import get_profile
from botnassimgnl.routes.helpers import app_settings, form_ids
from botnassimgnl.sender import active_job, start_job

bp = Blueprint("relances", __name__, url_prefix="/relances")


@bp.get("/")
def index():
    conn = get_db()
    settings = app_settings()
    expired = expire_followups(conn, settings)
    if expired:
        flash(f"{expired} contact(s) passe(s) en « Sans reponse » apres la derniere relance.", "info")
    return render_template("relances.html", due=due_followups(conn, settings), job=active_job())


@bp.post("/send")
def send():
    conn = get_db()
    settings = app_settings()
    if not settings.smtp_configured:
        flash("SMTP non configure : remplis le fichier .env puis relance le site.", "error")
        return redirect(url_for("relances.index"))
    if active_job():
        flash("Un envoi est deja en cours.", "error")
        return redirect(url_for("relances.index"))
    due_ids = {c["id"] for c in due_followups(conn, settings)}
    selected = [cid for cid in form_ids() if cid in due_ids]
    preparation = prepare_followups(conn, get_contacts(conn, selected))
    for reason in preparation.skipped[:10]:
        flash(f"Ignore — {reason}", "info")
    if not preparation.emails:
        flash("Aucune relance a envoyer.", "error")
        return redirect(url_for("relances.index"))
    profile = get_profile(conn)
    sender_name = settings.sender_name or f"{profile['prenom']} {profile['nom']}".strip()
    job = start_job(settings, preparation.emails, sender_name)
    flash(f"{len(preparation.emails)} relance(s) en cours d'envoi.", "success")
    return redirect(url_for("compose.index", job=job.id))
