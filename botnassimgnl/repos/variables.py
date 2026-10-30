"""Variables personnalisees creees avec le bouton + (ex : {Portfolio}, {Ville})."""

import re
import sqlite3

from botnassimgnl.templating import RESERVED_NAMES

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,29}$")
MAX_VALUE_LENGTH = 500


class VariableError(ValueError):
    """Variable invalide."""


def _clean_name(raw: str) -> str:
    name = (raw or "").strip().strip("{}").strip().replace(" ", "_")
    if not NAME_PATTERN.match(name):
        raise VariableError("Nom invalide : lettres, chiffres et _ uniquement, en commencant par une lettre (30 max)")
    if name.lower() in RESERVED_NAMES:
        raise VariableError(f"{{{name}}} existe deja comme variable integree")
    return name


def _clean_value(raw: str) -> str:
    value = (raw or "").strip()
    if len(value) > MAX_VALUE_LENGTH:
        raise VariableError(f"Valeur trop longue ({MAX_VALUE_LENGTH} caracteres max)")
    return value


def list_variables(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT id, name, value FROM custom_variables ORDER BY name COLLATE NOCASE").fetchall()
    return [dict(row) for row in rows]


def create_variable(conn: sqlite3.Connection, name: str, value: str) -> dict:
    clean_name, clean_value = _clean_name(name), _clean_value(value)
    try:
        cursor = conn.execute("INSERT INTO custom_variables (name, value) VALUES (?, ?)", (clean_name, clean_value))
    except sqlite3.IntegrityError as exc:
        raise VariableError(f"{{{clean_name}}} existe deja") from exc
    conn.commit()
    return {"id": cursor.lastrowid, "name": clean_name, "value": clean_value}


def update_variable(conn: sqlite3.Connection, variable_id: int, value: str) -> None:
    conn.execute("UPDATE custom_variables SET value = ? WHERE id = ?", (_clean_value(value), variable_id))
    conn.commit()


def delete_variable(conn: sqlite3.Connection, variable_id: int) -> None:
    conn.execute("DELETE FROM custom_variables WHERE id = ?", (variable_id,))
    conn.commit()
