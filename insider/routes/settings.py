from flask import Blueprint, flash, redirect, render_template, url_for

from insider.config import SMTP_PRESETS
from insider.db import get_db
from insider.inbox import InboxError, check_inbox
from insider.mailer import MailerError, test_connection
from insider.repos.emails import sent_today
from insider.routes.helpers import app_settings

bp = Blueprint("settings", __name__, url_prefix="/parametres")


@bp.get("/")
def index():
    return render_template("settings.html", presets=SMTP_PRESETS, sent_today=sent_today(get_db()))


@bp.post("/test-smtp")
def test_smtp():
    try:
        test_connection(app_settings())
    except MailerError as exc:
        flash(f"Connexion SMTP echouee : {exc}", "error")
    else:
        flash("Connexion SMTP OK — les emails peuvent partir.", "success")
    return redirect(url_for("settings.index"))


@bp.post("/test-imap")
def test_imap():
    try:
        report = check_inbox(get_db(), app_settings())
    except InboxError as exc:
        flash(f"Connexion IMAP echouee : {exc}", "error")
    else:
        flash(f"Connexion IMAP OK — {report.scanned} message(s) analyse(s).", "success")
    return redirect(url_for("settings.index"))
