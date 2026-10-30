from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from botnassimgnl.db import get_db
from botnassimgnl.email_format import EmailFormatError, build_email
from botnassimgnl.repos.institutions import (InstitutionError, create_institution, delete_institution,
                                        list_institutions, update_institution)

bp = Blueprint("formats", __name__, url_prefix="/formats")


def _patterns_from_form() -> list[str]:
    return [p for p in request.form.getlist("patterns") if p.strip()]


@bp.get("/")
def index():
    search = request.args.get("search", "")
    return render_template("formats.html", institutions=list_institutions(get_db(), search), search=search)


@bp.post("/")
def create():
    try:
        create_institution(get_db(), request.form.get("name", ""), _patterns_from_form())
    except (InstitutionError, EmailFormatError) as exc:
        flash(str(exc), "error")
    else:
        flash(f"Institution « {request.form.get('name', '').strip()} » ajoutee.", "success")
    return redirect(url_for("formats.index"))


@bp.post("/<int:institution_id>")
def update(institution_id: int):
    try:
        update_institution(get_db(), institution_id, request.form.get("name", ""), _patterns_from_form())
    except (InstitutionError, EmailFormatError) as exc:
        flash(str(exc), "error")
    else:
        flash("Institution mise a jour.", "success")
    return redirect(url_for("formats.index", search=request.args.get("search", "")))


@bp.post("/<int:institution_id>/delete")
def delete(institution_id: int):
    delete_institution(get_db(), institution_id)
    flash("Institution supprimee (les contacts existants sont conserves).", "success")
    return redirect(url_for("formats.index"))


@bp.get("/preview")
def preview():
    """Teste un format avec un prenom / nom (aperçu en direct)."""
    try:
        email = build_email(request.args.get("pattern", ""), request.args.get("prenom", "John"),
                            request.args.get("nom", "Smith"))
    except EmailFormatError as exc:
        return jsonify({"ok": False, "error": str(exc)})
    return jsonify({"ok": True, "email": email})
