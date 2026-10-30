"""Remplissage initial de la base (une seule fois)."""

import sqlite3

from insider.repos.institutions import create_institution
from insider.repos.templates import create_template
from insider.seed_data import INSTITUTIONS, TEMPLATES, expand_format

SEED_FLAG = "seeded_v1"


def seed_if_empty(conn: sqlite3.Connection) -> bool:
    """Ajoute banques et templates par defaut au premier lancement (une seule transaction)."""
    if conn.execute("SELECT 1 FROM meta WHERE key = ?", (SEED_FLAG,)).fetchone():
        return False
    for name, entries in INSTITUTIONS:
        create_institution(conn, name, [expand_format(entry) for entry in entries], commit=False)
    for name, lang, category, step, subject, body in TEMPLATES:
        create_template(conn, {"name": name, "lang": lang, "category": category,
                               "followup_step": step, "subject": subject, "body": body}, commit=False)
    conn.execute("INSERT INTO meta (key, value) VALUES (?, datetime('now'))", (SEED_FLAG,))
    conn.commit()
    return True
