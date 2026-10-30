"""Contacts : creation, import, recherche et mise a jour du statut."""

import re
import sqlite3
from dataclasses import dataclass, field

from botnassimgnl import statuses
from botnassimgnl.email_format import EmailFormatError, build_email
from botnassimgnl.repos.institutions import find_patterns

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.IGNORECASE)
CIVILITES = ("Monsieur", "Madame")
EDITABLE_FIELDS = ("civilite", "prenom", "nom", "poste", "institution", "email", "notes", "lang")


class ContactError(ValueError):
    """Donnees de contact invalides."""


@dataclass(frozen=True)
class ImportReport:
    created: int = 0
    duplicates: int = 0
    without_email: int = 0
    errors: list[str] = field(default_factory=list)


def resolve_email(conn: sqlite3.Connection, prenom: str, nom: str, institution: str,
                  email: str = "", format_index: int = 0) -> str:
    """Email fourni s'il est valide, sinon genere depuis le format de l'institution."""
    explicit = (email or "").strip().lower()
    if explicit:
        if not EMAIL_PATTERN.match(explicit):
            raise ContactError(f"Email invalide : {explicit}")
        return explicit
    patterns = find_patterns(conn, institution)
    if not patterns:
        return ""
    pattern = patterns[format_index] if 0 <= format_index < len(patterns) else patterns[0]
    try:
        return build_email(pattern, prenom, nom)
    except EmailFormatError as exc:
        raise ContactError(str(exc)) from exc


def _validated(data: dict) -> dict:
    prenom = (data.get("prenom") or "").strip()
    nom = (data.get("nom") or "").strip()
    if not prenom or not nom:
        raise ContactError("Prenom et nom sont requis")
    civilite = (data.get("civilite") or "Monsieur").strip()
    lang = data.get("lang") if data.get("lang") in ("fr", "en") else "fr"
    return {
        "civilite": civilite if civilite in CIVILITES else "Monsieur",
        "prenom": prenom,
        "nom": nom,
        "poste": (data.get("poste") or "").strip(),
        "institution": (data.get("institution") or "").strip(),
        "lang": lang,
    }


def create_contact(conn: sqlite3.Connection, data: dict, format_index: int = 0) -> int:
    clean = _validated(data)
    email = resolve_email(conn, clean["prenom"], clean["nom"], clean["institution"],
                          data.get("email", ""), format_index)
    try:
        cursor = conn.execute(
            """INSERT INTO contacts (civilite, prenom, nom, poste, institution, email, lang)
               VALUES (:civilite, :prenom, :nom, :poste, :institution, :email, :lang)""",
            {**clean, "email": email},
        )
    except sqlite3.IntegrityError as exc:
        raise ContactError(f"Un contact existe deja avec l'email {email}") from exc
    conn.commit()
    return cursor.lastrowid


def import_rows(conn: sqlite3.Connection, rows: list[dict], lang: str = "fr") -> ImportReport:
    created = duplicates = without_email = 0
    errors: list[str] = []
    for index, row in enumerate(rows, start=2):
        try:
            contact_id = create_contact(conn, {**row, "lang": lang})
        except ContactError as exc:
            if "existe deja" in str(exc):
                duplicates += 1
            else:
                errors.append(f"Ligne {index} : {exc}")
            continue
        created += 1
        email = conn.execute("SELECT email FROM contacts WHERE id = ?", (contact_id,)).fetchone()["email"]
        if not email:
            without_email += 1
    return ImportReport(created, duplicates, without_email, errors)


def list_contacts(conn: sqlite3.Connection, search: str = "", institution: str = "",
                  poste: str = "", status: str = "", limit: int | None = None) -> list[dict]:
    clauses, params = [], []
    if search.strip():
        like = f"%{search.strip()}%"
        clauses.append("(prenom LIKE ? OR nom LIKE ? OR email LIKE ? OR institution LIKE ? OR poste LIKE ?)")
        params.extend([like] * 5)
    if institution:
        clauses.append("institution = ? COLLATE NOCASE")
        params.append(institution)
    if poste:
        clauses.append("poste = ? COLLATE NOCASE")
        params.append(poste)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_sql = f"LIMIT {int(limit)}" if limit else ""
    rows = conn.execute(
        f"""SELECT c.*, (SELECT COUNT(*) FROM emails e WHERE e.contact_id = c.id AND e.ok = 1
                         AND e.kind <> 'test') AS email_count
            FROM contacts c {where}
            ORDER BY c.created_at DESC, c.id DESC {limit_sql}""",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def get_contact(conn: sqlite3.Connection, contact_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    return dict(row) if row else None


def get_contacts(conn: sqlite3.Connection, ids: list[int]) -> list[dict]:
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(f"SELECT * FROM contacts WHERE id IN ({placeholders}) ORDER BY id", ids).fetchall()
    return [dict(row) for row in rows]


def update_contact(conn: sqlite3.Connection, contact_id: int, data: dict) -> None:
    current = get_contact(conn, contact_id)
    if current is None:
        raise ContactError("Contact introuvable")
    merged = {**current, **{k: v for k, v in data.items() if k in EDITABLE_FIELDS}}
    clean = _validated(merged)
    email = (merged.get("email") or "").strip().lower()
    if email and not EMAIL_PATTERN.match(email):
        raise ContactError(f"Email invalide : {email}")
    try:
        conn.execute(
            """UPDATE contacts SET civilite=:civilite, prenom=:prenom, nom=:nom, poste=:poste,
               institution=:institution, lang=:lang, email=:email, notes=:notes,
               updated_at=datetime('now') WHERE id=:id""",
            {**clean, "email": email, "notes": (merged.get("notes") or "").strip(), "id": contact_id},
        )
    except sqlite3.IntegrityError as exc:
        raise ContactError(f"Un contact existe deja avec l'email {email}") from exc
    conn.commit()


def set_status(conn: sqlite3.Connection, contact_ids: list[int], status: str) -> int:
    if not statuses.is_valid(status):
        raise ContactError(f"Statut inconnu : {status}")
    if not contact_ids:
        return 0
    placeholders = ",".join("?" * len(contact_ids))
    replied_sql = ", replied_at = COALESCE(replied_at, datetime('now'))" if status in statuses.REPLIED else ""
    cursor = conn.execute(
        f"UPDATE contacts SET status = ?, updated_at = datetime('now'){replied_sql} WHERE id IN ({placeholders})",
        [status, *contact_ids],
    )
    conn.commit()
    return cursor.rowcount


def delete_contacts(conn: sqlite3.Connection, contact_ids: list[int]) -> int:
    if not contact_ids:
        return 0
    placeholders = ",".join("?" * len(contact_ids))
    cursor = conn.execute(f"DELETE FROM contacts WHERE id IN ({placeholders})", contact_ids)
    conn.commit()
    return cursor.rowcount


def distinct_values(conn: sqlite3.Connection, column: str) -> list[str]:
    if column not in ("institution", "poste"):
        raise ValueError(column)
    rows = conn.execute(
        f"SELECT DISTINCT {column} AS v FROM contacts WHERE {column} <> '' ORDER BY {column} COLLATE NOCASE"
    ).fetchall()
    return [row["v"] for row in rows]


def grouped_counts(conn: sqlite3.Connection, column: str) -> list[dict]:
    if column not in ("institution", "poste"):
        raise ValueError(column)
    rows = conn.execute(
        f"""SELECT COALESCE(NULLIF({column}, ''), '—') AS name, COUNT(*) AS total,
                   SUM(status <> 'non_contacte') AS contacted,
                   SUM(status IN ('repondu','entretien','offre','refuse')) AS replied
            FROM contacts GROUP BY name ORDER BY total DESC, name"""
    ).fetchall()
    return [dict(row) for row in rows]
