"""Bot de candidatures — application Flask."""

import logging
import secrets

from flask import Flask, abort, request, session

from insider import statuses
from insider.config import Settings, load_settings
from insider.db import close_db, connect, init_schema
from insider.seed import seed_if_empty

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
CSRF_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _init_storage(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(settings.database_path)
    try:
        init_schema(conn)
        seed_if_empty(conn)
    finally:
        conn.close()


def _csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def _check_csrf() -> None:
    """Bloque les formulaires envoyes depuis un autre site vers ton serveur local."""
    if request.method in CSRF_SAFE_METHODS:
        return
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not sent or not secrets.compare_digest(sent, session.get("csrf_token", "")):
        abort(400, description="Jeton de securite invalide. Recharge la page et recommence.")


def create_app(settings: Settings | None = None) -> Flask:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app_settings = settings or load_settings()
    _init_storage(app_settings)

    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.update(SECRET_KEY=app_settings.secret_key, SETTINGS=app_settings,
                      MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES)
    app.teardown_appcontext(close_db)
    app.before_request(_check_csrf)

    @app.context_processor
    def inject_globals() -> dict:
        return {"csrf_token": _csrf_token, "STATUSES": statuses.STATUSES,
                "settings": app_settings, "status_label": statuses.label}

    from insider.routes import register_blueprints

    register_blueprints(app)
    return app
