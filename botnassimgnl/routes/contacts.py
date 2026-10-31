from flask import (Blueprint, flash, jsonify, redirect, render_template, request,
                   send_from_directory, url_for)

from botnassimgnl.csv_import import ImportFileError, parse_contacts_file
from botnassimgnl.db import get_db
from botnassimgnl.email_format import EmailFormatError
from botnassimgnl.repos import contacts as repo
from botnassimgnl.repos.emails import history
from botnassimgnl.repos.institutions import find_patterns, list_institutions
from botnassimgnl.routes.helpers import form_ids

bp = Blueprint("contacts", __name__, url_prefix="/contacts")

TABS = ("tous", "institution", "poste", "ajouter")


def _filters() -> dict:
    return {key: request.args.get(key, "").strip() for key in ("search", "institution", "poste", "status")}


@bp.get("/")
def index():
    conn = get_db()
    tab = request.args.get("tab", "tous")
    filters = _filters()
    contacts = repo.list_contacts(conn, **filters)
    return render_template(
        "contacts.html",
        tab=tab if tab in TABS else "tous",
        contacts=contacts,
        filters=filters,
        total=len(repo.list_contacts(conn)),
        institutions=repo.distinct_values(conn, "institution"),
        postes=repo.distinct_values(conn, "poste"),
        by_institution=repo.grouped_counts(conn, "institution"),
        by_poste=repo.grouped_counts(conn, "poste"),
        known_institutions=list_institutions(conn),
    )


@bp.post("/add")
def add():
    data = request.form.to_dict()
    format_index = int(data.get("format_index") or 0)
    try:
        repo.create_contact(get_db(), data, format_index)
    except (repo.ContactError, EmailFormatError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("contacts.index", tab="ajouter"))
    flash(f"Contact {data.get('prenom')} {data.get('nom')} ajoute.", "success")
    return redirect(url_for("contacts.index", tab="ajouter"))


@bp.post("/import")
def import_file():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        flash("Choisis un fichier CSV ou Excel.", "error")
        return redirect(url_for("contacts.index", tab="ajouter"))
    try:
        parsed = parse_contacts_file(upload.filename, upload.read())
    except ImportFileError as exc:
        flash(f"Import impossible : {exc}", "error")
        return redirect(url_for("contacts.index", tab="ajouter"))
    report = repo.import_rows(get_db(), parsed.rows, request.form.get("lang", "fr"))
    message = f"{report.created} contact(s) importe(s), {report.duplicates} doublon(s) ignore(s)."
    if report.without_email:
        message += f" {report.without_email} sans email (institution sans format : ajoute-la dans Formats mail)."
    flash(message, "success")
    for error in (parsed.errors + report.errors)[:10]:
        flash(error, "error")
    return redirect(url_for("contacts.index"))


@bp.get("/template.csv")
def template_csv():
    return send_from_directory("../static", "template_import_contacts.csv", as_attachment=True)


@bp.get("/email-preview")
def email_preview():
    """Email genere en direct pendant la saisie d'un contact."""
    args = request.args
    try:
        email = repo.resolve_email(get_db(), args.get("prenom", ""), args.get("nom", ""),
                                   args.get("institution", ""), "", int(args.get("format_index") or 0))
    except repo.ContactError:
        email = ""
    return jsonify({"email": email, "formats": find_patterns(get_db(), args.get("institution", ""))})


@bp.get("/<int:contact_id>")
def detail(contact_id: int):
    conn = get_db()
    contact = repo.get_contact(conn, contact_id)
    if contact is None:
        flash("Contact introuvable.", "error")
        return redirect(url_for("contacts.index"))
    return render_template("contact_detail.html", contact=contact, emails=history(conn, contact_id))


@bp.post("/<int:contact_id>")
def update(contact_id: int):
    try:
        repo.update_contact(get_db(), contact_id, request.form.to_dict())
        if request.form.get("status"):
            repo.set_status(get_db(), [contact_id], request.form["status"])
    except repo.ContactError as exc:
        flash(str(exc), "error")
    else:
        flash("Contact mis a jour.", "success")
    return redirect(url_for("contacts.detail", contact_id=contact_id))


@bp.post("/bulk")
def bulk():
    ids = form_ids()
    # Le menu « Changer le statut » partage le nom "action" : on garde la premiere valeur non vide.
    action = next((value for value in request.form.getlist("action") if value), "")
    if not ids:
        flash("Aucun contact selectionne.", "error")
    elif action == "delete":
        flash(f"{repo.delete_contacts(get_db(), ids)} contact(s) supprime(s).", "success")
    elif action == "compose":
        return redirect(url_for("compose.index", ids=",".join(map(str, ids))))
    elif action.startswith("status:"):
        try:
            count = repo.set_status(get_db(), ids, action.split(":", 1)[1])
        except repo.ContactError as exc:
            flash(str(exc), "error")
        else:
            flash(f"Statut mis a jour pour {count} contact(s).", "success")
    return redirect(request.referrer or url_for("contacts.index"))
