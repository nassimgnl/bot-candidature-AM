from pathlib import Path

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from botnassimgnl.campaigns import prepare_initial
from botnassimgnl.db import get_db
from botnassimgnl.mailer import MailerError, OutgoingEmail, send_email
from botnassimgnl.repos import templates as template_repo
from botnassimgnl.repos.contacts import get_contact, get_contacts, list_contacts
from botnassimgnl.repos.profile import get_profile
from botnassimgnl.routes.helpers import app_settings, form_ids
from botnassimgnl.routes.profile import save_upload
from botnassimgnl.sender import active_job, get_job, start_job
from botnassimgnl.templating import VARIABLES_HELP, build_context, render

bp = Blueprint("compose", __name__, url_prefix="/compose")

ATTACHMENT_EXTENSIONS = (".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg")
SAMPLE_CONTACT = {"civilite": "Monsieur", "prenom": "Jean", "nom": "Dupont",
                  "poste": "Head of Trading", "institution": "BNP Paribas"}


def _sender_name(profile: dict) -> str:
    return app_settings().sender_name or f"{profile['prenom']} {profile['nom']}".strip()


def _attachments(profile: dict) -> tuple[Path, ...]:
    files: list[Path] = []
    if request.form.get("attach_cv") and profile["cv_filename"]:
        cv_path = app_settings().uploads_dir / profile["cv_filename"]
        if cv_path.exists():
            files.append(cv_path)
    upload = request.files.get("attachment")
    if upload is not None and upload.filename:
        files.append(save_upload(upload, ATTACHMENT_EXTENSIONS))
    return tuple(files)


@bp.get("/")
def index():
    conn = get_db()
    preselected = [int(v) for v in request.args.get("ids", "").split(",") if v.isdigit()]
    return render_template(
        "compose.html",
        templates=template_repo.list_templates(conn),
        categories=template_repo.CATEGORIES,
        contacts=[c for c in list_contacts(conn) if c["email"]],
        preselected=preselected,
        profile=get_profile(conn),
        variables=VARIABLES_HELP,
        job=get_job(request.args.get("job", "")) or active_job(),
    )


@bp.post("/preview")
def preview():
    payload = request.get_json(silent=True) or {}
    conn = get_db()
    contact = get_contact(conn, int(payload["contact_id"])) if str(payload.get("contact_id", "")).isdigit() else None
    context = build_context(contact or SAMPLE_CONTACT, get_profile(conn))
    return jsonify({
        "to": contact["email"] if contact else "(exemple)",
        "subject": render(payload.get("subject", ""), context),
        "body": render(payload.get("body", ""), context),
    })


@bp.post("/send")
def send():
    conn = get_db()
    settings = app_settings()
    if not settings.smtp_configured:
        flash("SMTP non configure : remplis le fichier .env puis relance le site.", "error")
        return redirect(url_for("compose.index"))
    if active_job():
        flash("Un envoi est deja en cours. Attends qu'il se termine ou arrete-le.", "error")
        return redirect(url_for("compose.index"))
    subject, body = request.form.get("subject", "").strip(), request.form.get("body", "").strip()
    if not subject or not body:
        flash("Le sujet et le message sont obligatoires.", "error")
        return redirect(url_for("compose.index"))
    profile = get_profile(conn)
    try:
        attachments = _attachments(profile)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("compose.index"))
    preparation = prepare_initial(conn, get_contacts(conn, form_ids()), subject, body,
                                  attachments, force=bool(request.form.get("force")))
    for reason in preparation.skipped[:10]:
        flash(f"Ignore — {reason}", "info")
    if not preparation.emails:
        flash("Aucun email a envoyer.", "error")
        return redirect(url_for("compose.index"))
    job = start_job(settings, preparation.emails, _sender_name(profile))
    flash(f"Envoi lance : {len(preparation.emails)} email(s), un toutes les {settings.send_delay_seconds} s.", "success")
    return redirect(url_for("compose.index", job=job.id))


@bp.post("/test")
def send_test():
    """Envoie le mail a sa propre adresse pour verifier le rendu."""
    conn = get_db()
    settings = app_settings()
    profile = get_profile(conn)
    ids = form_ids()
    contact = get_contact(conn, ids[0]) if ids else None
    context = build_context(contact or SAMPLE_CONTACT, profile)
    try:
        attachments = _attachments(profile)
        send_email(settings, OutgoingEmail(to=settings.smtp_user,
                                           subject="[TEST] " + render(request.form.get("subject", ""), context),
                                           body=render(request.form.get("body", ""), context),
                                           attachments=attachments), _sender_name(profile))
    except (MailerError, ValueError) as exc:
        flash(f"Mail test non envoye : {exc}", "error")
    else:
        flash(f"Mail test envoye a {settings.smtp_user}. Va voir ta boite !", "success")
    return redirect(url_for("compose.index"))


@bp.get("/job/<job_id>")
def job_status(job_id: str):
    job = get_job(job_id)
    return (jsonify(job.to_dict()), 200) if job else (jsonify({"error": "introuvable"}), 404)


@bp.post("/job/<job_id>/stop")
def job_stop(job_id: str):
    job = get_job(job_id)
    if job:
        job.cancel_event.set()
    return jsonify({"ok": bool(job)})


@bp.post("/templates")
def template_create():
    try:
        template_repo.create_template(get_db(), request.form.to_dict())
    except template_repo.TemplateError as exc:
        flash(str(exc), "error")
    else:
        flash("Template sauvegarde.", "success")
    return redirect(url_for("compose.index"))


@bp.post("/templates/<int:template_id>")
def template_update(template_id: int):
    try:
        template_repo.update_template(get_db(), template_id, request.form.to_dict())
    except template_repo.TemplateError as exc:
        flash(str(exc), "error")
    else:
        flash("Template mis a jour.", "success")
    return redirect(url_for("compose.index"))


@bp.post("/templates/<int:template_id>/delete")
def template_delete(template_id: int):
    template_repo.delete_template(get_db(), template_id)
    flash("Template supprime.", "success")
    return redirect(url_for("compose.index"))
