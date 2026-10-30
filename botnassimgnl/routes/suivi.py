from flask import Blueprint, render_template, request

from botnassimgnl.db import get_db
from botnassimgnl.repos.contacts import list_contacts

bp = Blueprint("suivi", __name__, url_prefix="/suivi")


@bp.get("/")
def index():
    status = request.args.get("status", "")
    contacts = list_contacts(get_db(), status=status)
    return render_template("suivi.html", contacts=contacts, status=status)
