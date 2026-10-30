from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from botnassimgnl.db import get_db
from botnassimgnl.repos.profile import get_profile, set_cv_filename, update_profile
from botnassimgnl.routes.helpers import app_settings

bp = Blueprint("profile", __name__, url_prefix="/profil")

CV_EXTENSIONS = (".pdf", ".doc", ".docx")


def save_upload(upload, allowed_extensions: tuple[str, ...]) -> Path:
    """Enregistre un fichier envoye dans data/uploads et renvoie son chemin."""
    filename = secure_filename(upload.filename or "")
    if not filename or not filename.lower().endswith(allowed_extensions):
        raise ValueError(f"Formats acceptes : {', '.join(allowed_extensions)}")
    destination = app_settings().uploads_dir / filename
    upload.save(destination)
    return destination


@bp.get("/")
def index():
    return render_template("profile.html", profile=get_profile(get_db()))


@bp.post("/")
def save():
    conn = get_db()
    update_profile(conn, request.form.to_dict())
    upload = request.files.get("cv")
    if upload is not None and upload.filename:
        try:
            set_cv_filename(conn, save_upload(upload, CV_EXTENSIONS).name)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("profile.index"))
    flash("Profil sauvegarde.", "success")
    return redirect(url_for("profile.index"))


@bp.post("/cv/delete")
def delete_cv():
    set_cv_filename(get_db(), "")
    flash("CV retire du profil.", "success")
    return redirect(url_for("profile.index"))
