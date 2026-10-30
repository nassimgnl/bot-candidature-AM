"""Templates d'email (Candidature, Coffee Chat, Relance ; FR / EN)."""

import sqlite3

LANGS = ("fr", "en")
CATEGORIES = {"candidature": "Candidature", "coffee_chat": "Coffee Chat", "relance": "Relance"}


class TemplateError(ValueError):
    """Template invalide."""


def _validated(data: dict) -> dict:
    name = (data.get("name") or "").strip()
    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()
    lang = data.get("lang")
    category = data.get("category")
    if not name or not subject or not body:
        raise TemplateError("Nom, sujet et message sont requis")
    if lang not in LANGS or category not in CATEGORIES:
        raise TemplateError("Langue ou categorie invalide")
    step = data.get("followup_step")
    step_value = int(step) if category == "relance" and str(step or "").isdigit() else None
    return {"name": name, "subject": subject, "body": body, "lang": lang,
            "category": category, "followup_step": step_value}


def list_templates(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM templates ORDER BY lang, category, COALESCE(followup_step, 0), id"
    ).fetchall()
    return [dict(row) for row in rows]


def get_template(conn: sqlite3.Connection, template_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
    return dict(row) if row else None


def followup_template(conn: sqlite3.Connection, lang: str, step: int) -> dict | None:
    """Template de relance pour l'etape donnee (ou la plus proche en dessous)."""
    row = conn.execute(
        """SELECT * FROM templates WHERE category = 'relance' AND lang = ?
           ORDER BY (followup_step IS NULL), ABS(COALESCE(followup_step, 99) - ?), id LIMIT 1""",
        (lang, step),
    ).fetchone()
    return dict(row) if row else None


def create_template(conn: sqlite3.Connection, data: dict, commit: bool = True) -> int:
    clean = _validated(data)
    cursor = conn.execute(
        """INSERT INTO templates (name, lang, category, followup_step, subject, body)
           VALUES (:name, :lang, :category, :followup_step, :subject, :body)""",
        clean,
    )
    if commit:
        conn.commit()
    return cursor.lastrowid


def update_template(conn: sqlite3.Connection, template_id: int, data: dict) -> None:
    clean = _validated(data)
    cursor = conn.execute(
        """UPDATE templates SET name=:name, lang=:lang, category=:category, followup_step=:followup_step,
           subject=:subject, body=:body WHERE id=:id""",
        {**clean, "id": template_id},
    )
    if cursor.rowcount == 0:
        raise TemplateError("Template introuvable")
    conn.commit()


def delete_template(conn: sqlite3.Connection, template_id: int) -> None:
    conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
