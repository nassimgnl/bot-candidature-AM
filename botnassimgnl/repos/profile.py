"""Profil de l'utilisateur (utilise dans les templates)."""

import sqlite3

PROFILE_FIELDS = ("prenom", "nom", "ecole", "poste_actuel", "telephone", "linkedin")


def normalize_url(raw: str) -> str:
    """'linkedin.com/in/moi' -> 'https://linkedin.com/in/moi' (lien cliquable dans les mails)."""
    url = (raw or "").strip()
    if url and not url.lower().startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def get_profile(conn: sqlite3.Connection) -> dict:
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    return dict(row) if row else {field: "" for field in (*PROFILE_FIELDS, "cv_filename")}


def update_profile(conn: sqlite3.Connection, data: dict) -> None:
    values = {field: (data.get(field) or "").strip() for field in PROFILE_FIELDS}
    values = {**values, "linkedin": normalize_url(values["linkedin"])}
    assignments = ", ".join(f"{field} = :{field}" for field in PROFILE_FIELDS)
    conn.execute(f"UPDATE profile SET {assignments} WHERE id = 1", values)
    conn.commit()


def set_cv_filename(conn: sqlite3.Connection, filename: str) -> None:
    conn.execute("UPDATE profile SET cv_filename = ? WHERE id = 1", (filename,))
    conn.commit()
