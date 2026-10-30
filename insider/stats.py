"""Chiffres du Dashboard et d'Analytics."""

import sqlite3


def overview(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        """SELECT COUNT(*) AS contacts,
                  SUM(date(created_at, 'localtime') = date('now', 'localtime')) AS contacts_today,
                  SUM(status <> 'non_contacte') AS contacted,
                  SUM(status IN ('repondu', 'entretien', 'offre', 'refuse')) AS replies,
                  SUM(status IN ('entretien', 'offre')) AS interviews,
                  SUM(status = 'offre') AS offers
           FROM contacts"""
    ).fetchone()
    sent = conn.execute("SELECT COUNT(*) AS n FROM emails WHERE ok = 1 AND kind <> 'test'").fetchone()["n"]
    values = {key: row[key] or 0 for key in row.keys()}
    contacted = values["contacted"]
    return {
        **values,
        "emails_sent": sent,
        "reply_rate": round(100 * values["replies"] / contacted) if contacted else 0,
    }


def status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute("SELECT status, COUNT(*) AS n FROM contacts GROUP BY status").fetchall()
    return {row["status"]: row["n"] for row in rows}
