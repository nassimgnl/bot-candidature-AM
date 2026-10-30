"""Banques / institutions et leurs formats d'email."""

import sqlite3

from insider.email_format import format_example, validate_format


class InstitutionError(ValueError):
    """Donnees d'institution invalides."""


def _clean_patterns(patterns: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in patterns:
        if not (raw or "").strip():
            continue
        pattern = validate_format(raw)
        if pattern not in cleaned:
            cleaned.append(pattern)
    return cleaned


def list_institutions(conn: sqlite3.Connection, search: str = "") -> list[dict]:
    rows = conn.execute(
        """
        SELECT i.id, i.name,
               (SELECT COUNT(*) FROM contacts c WHERE c.institution = i.name COLLATE NOCASE) AS contact_count
        FROM institutions i
        WHERE i.name LIKE ? COLLATE NOCASE
        ORDER BY i.name COLLATE NOCASE
        """,
        (f"%{search.strip()}%",),
    ).fetchall()
    formats = conn.execute("SELECT id, institution_id, pattern FROM email_formats ORDER BY position, id").fetchall()
    by_institution: dict[int, list[dict]] = {}
    for fmt in formats:
        by_institution.setdefault(fmt["institution_id"], []).append(
            {"id": fmt["id"], "pattern": fmt["pattern"], "example": format_example(fmt["pattern"])}
        )
    return [{**dict(row), "formats": by_institution.get(row["id"], [])} for row in rows]


def find_patterns(conn: sqlite3.Connection, name: str) -> list[str]:
    """Formats d'une institution (par nom, insensible a la casse), le premier etant le defaut."""
    rows = conn.execute(
        """
        SELECT f.pattern FROM email_formats f
        JOIN institutions i ON i.id = f.institution_id
        WHERE i.name = ? COLLATE NOCASE
        ORDER BY f.position, f.id
        """,
        ((name or "").strip(),),
    ).fetchall()
    return [row["pattern"] for row in rows]


def _write_patterns(conn: sqlite3.Connection, institution_id: int, patterns: list[str]) -> None:
    conn.execute("DELETE FROM email_formats WHERE institution_id = ?", (institution_id,))
    conn.executemany(
        "INSERT INTO email_formats (institution_id, pattern, position) VALUES (?, ?, ?)",
        [(institution_id, pattern, position) for position, pattern in enumerate(patterns)],
    )


def _clean_name(name: str) -> str:
    clean = (name or "").strip()
    if not clean:
        raise InstitutionError("Le nom de l'institution est requis")
    return clean


def create_institution(conn: sqlite3.Connection, name: str, patterns: list[str], commit: bool = True) -> int:
    clean_name = _clean_name(name)
    clean_patterns = _clean_patterns(patterns)
    try:
        cursor = conn.execute("INSERT INTO institutions (name) VALUES (?)", (clean_name,))
    except sqlite3.IntegrityError as exc:
        raise InstitutionError(f"L'institution « {clean_name} » existe deja") from exc
    _write_patterns(conn, cursor.lastrowid, clean_patterns)
    if commit:
        conn.commit()
    return cursor.lastrowid


def update_institution(conn: sqlite3.Connection, institution_id: int, name: str, patterns: list[str]) -> None:
    clean_name = _clean_name(name)
    clean_patterns = _clean_patterns(patterns)
    current = conn.execute("SELECT name FROM institutions WHERE id = ?", (institution_id,)).fetchone()
    if current is None:
        raise InstitutionError("Institution introuvable")
    try:
        conn.execute("UPDATE institutions SET name = ? WHERE id = ?", (clean_name, institution_id))
    except sqlite3.IntegrityError as exc:
        raise InstitutionError(f"L'institution « {clean_name} » existe deja") from exc
    # Les contacts suivent le renommage.
    conn.execute(
        "UPDATE contacts SET institution = ? WHERE institution = ? COLLATE NOCASE",
        (clean_name, current["name"]),
    )
    _write_patterns(conn, institution_id, clean_patterns)
    conn.commit()


def delete_institution(conn: sqlite3.Connection, institution_id: int) -> None:
    conn.execute("DELETE FROM institutions WHERE id = ?", (institution_id,))
    conn.commit()
