from flask import Blueprint, jsonify, render_template, request

from insider import statuses
from insider.db import get_db
from insider.repos.contacts import ContactError, list_contacts, set_status

bp = Blueprint("pipeline", __name__, url_prefix="/pipeline")


@bp.get("/")
def index():
    contacts = list_contacts(get_db())
    columns = {key: [c for c in contacts if c["status"] == key] for key in statuses.STATUSES}
    return render_template("pipeline.html", columns=columns)


@bp.post("/move")
def move():
    payload = request.get_json(silent=True) or {}
    contact_id = payload.get("id")
    if not str(contact_id).isdigit():
        return jsonify({"ok": False, "error": "Contact invalide"}), 400
    try:
        set_status(get_db(), [int(contact_id)], payload.get("status", ""))
    except ContactError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True})
