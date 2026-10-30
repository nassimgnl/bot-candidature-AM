"""Historique des emails envoyes."""

import sqlite3
from datetime import date, timedelta


def record_email(conn: sqlite3.Connection, contact_id: int, kind: str, subject: str, body: str,
                 message_id: str | None, ok: bool, error: str | None = None) -> int:
    cursor = conn.execute(
        """INSERT INTO emails (contact_id, kind, subject, body, message_id, ok, error)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (contact_id, kind, subject, body, message_id, int(ok), error),
    )
    conn.commit()
    return cursor.lastrowid


def sent_today(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM emails WHERE ok = 1 AND kind <> 'test' AND date(sent_at, 'localtime') = date('now', 'localtime')"
    ).fetchone()
    return row["n"]


def first_email(conn: sqlite3.Connection, contact_id: int) -> dict | None:
    """Premier email envoye au contact : sert de fil pour les relances."""
    row = conn.execute(
        "SELECT * FROM emails WHERE contact_id = ? AND ok = 1 AND kind = 'initial' ORDER BY id LIMIT 1",
        (contact_id,),
    ).fetchone()
    return dict(row) if row else None


def history(conn: sqlite3.Connection, contact_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM emails WHERE contact_id = ? ORDER BY id DESC", (contact_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def message_ids_by_contact(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute("SELECT message_id, contact_id FROM emails WHERE message_id IS NOT NULL AND ok = 1").fetchall()
    return {row["message_id"]: row["contact_id"] for row in rows}


def sends_per_day(conn: sqlite3.Connection, days: int = 30, today: date | None = None) -> list[dict]:
    end = today or date.today()
    start = end - timedelta(days=days - 1)
    rows = conn.execute(
        """SELECT date(sent_at, 'localtime') AS day, COUNT(*) AS n FROM emails
           WHERE ok = 1 AND kind <> 'test' AND date(sent_at, 'localtime') >= ? GROUP BY day""",
        (start.isoformat(),),
    ).fetchall()
    counts = {row["day"]: row["n"] for row in rows}
    return [
        {"day": (start + timedelta(days=i)).isoformat(), "n": counts.get((start + timedelta(days=i)).isoformat(), 0)}
        for i in range(days)
    ]


def earliest_sent_date(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT MIN(sent_at) AS d FROM emails WHERE ok = 1").fetchone()
    return row["d"]
