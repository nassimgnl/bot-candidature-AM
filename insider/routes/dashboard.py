from flask import Blueprint, flash, redirect, render_template, request, url_for

from insider.campaigns import due_followups, expire_followups
from insider.db import get_db
from insider.inbox import InboxError, check_inbox
from insider.repos.contacts import list_contacts
from insider.routes.helpers import app_settings
from insider.stats import overview

bp = Blueprint("dashboard", __name__)

RECENT_CONTACTS = 8


@bp.get("/")
def index():
    conn = get_db()
    expire_followups(conn, app_settings())
    return render_template(
        "dashboard.html",
        stats=overview(conn),
        recent=list_contacts(conn, limit=RECENT_CONTACTS),
        followups_due=len(due_followups(conn, app_settings())),
    )


@bp.post("/inbox/check")
def inbox_check():
    try:
        report = check_inbox(get_db(), app_settings())
    except InboxError as exc:
        flash(str(exc), "error")
    else:
        flash(f"Inbox verifiee : {report.scanned} messages lus, {report.replies} nouvelle(s) reponse(s), "
              f"{report.bounces} bounce(s).", "success")
    return redirect(request.referrer or url_for("dashboard.index"))
