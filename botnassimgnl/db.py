"""Connexion SQLite et initialisation de la base."""

import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
# Colonnes ajoutees apres la premiere version : ajoutees aux bases existantes.
ADDED_PROFILE_COLUMNS = ("telephone", "linkedin")


def connect(database_path: Path | str) -> sqlite3.Connection:
    """Ouvre une connexion SQLite avec les reglages du projet."""
    conn = sqlite3.connect(database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _add_missing_profile_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(profile)")}
    for column in ADDED_PROFILE_COLUMNS:
        if column not in existing:
            conn.execute(f"ALTER TABLE profile ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    _add_missing_profile_columns(conn)
    conn.execute("INSERT OR IGNORE INTO profile (id) VALUES (1)")
    conn.commit()


def get_db() -> sqlite3.Connection:
    """Connexion propre a la requete Flask en cours."""
    if "db" not in g:
        g.db = connect(current_app.config["SETTINGS"].database_path)
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]
