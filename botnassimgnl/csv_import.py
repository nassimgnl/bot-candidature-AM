"""Lecture des fichiers CSV / Excel de contacts.

Colonnes reconnues (insensibles a la casse et aux accents) :
Prenom, Nom (requis), Institution, Poste, Civilite, Email.
"""

import csv
import io
import unicodedata
from dataclasses import dataclass, field

MAX_FILE_BYTES = 5 * 1024 * 1024
ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")

COLUMN_ALIASES = {
    "prenom": "prenom", "firstname": "prenom", "first name": "prenom", "first_name": "prenom",
    "nom": "nom", "lastname": "nom", "last name": "nom", "last_name": "nom", "name": "nom",
    "institution": "institution", "banque": "institution", "bank": "institution",
    "entreprise": "institution", "company": "institution", "societe": "institution",
    "poste": "poste", "position": "poste", "title": "poste", "titre": "poste",
    "civilite": "civilite", "genre": "civilite", "title civilite": "civilite",
    "email": "email", "e-mail": "email", "mail": "email", "adresse_email": "email",
}


class ImportFileError(ValueError):
    """Fichier illisible ou mal forme."""


@dataclass(frozen=True)
class ParsedRows:
    rows: list[dict]
    errors: list[str] = field(default_factory=list)


def _normalize_header(header: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(header or "").strip().lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _decode(raw: bytes) -> str:
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportFileError("Encodage du fichier non reconnu")


def _detect_delimiter(text: str) -> str:
    first_line = text.splitlines()[0] if text else ""
    counts = {d: first_line.count(d) for d in (";", ",", "\t")}
    return max(counts, key=counts.get) if any(counts.values()) else ","


def _read_csv(raw: bytes) -> list[list[str]]:
    text = _decode(raw)
    return list(csv.reader(io.StringIO(text), delimiter=_detect_delimiter(text)))


def _read_xlsx(raw: bytes) -> list[list[str]]:
    from openpyxl import load_workbook

    try:
        sheet = load_workbook(io.BytesIO(raw), read_only=True, data_only=True).active
    except Exception as exc:  # openpyxl leve plusieurs types d'erreurs
        raise ImportFileError(f"Fichier Excel illisible : {exc}") from exc
    return [["" if cell is None else str(cell) for cell in row] for row in sheet.iter_rows(values_only=True)]


def _map_header(header_row: list[str]) -> dict[int, str]:
    mapping = {}
    for index, header in enumerate(header_row):
        key = COLUMN_ALIASES.get(_normalize_header(header))
        if key and key not in mapping.values():
            mapping[index] = key
    if "prenom" not in mapping.values() or "nom" not in mapping.values():
        raise ImportFileError("Colonnes Prenom et Nom obligatoires")
    return mapping


def _normalize_civilite(value: str) -> str:
    lowered = value.strip().lower().rstrip(".")
    if lowered in ("m", "mr", "monsieur", "mister"):
        return "Monsieur"
    if lowered in ("mme", "mrs", "ms", "madame", "mlle"):
        return "Madame"
    return value.strip() or "Monsieur"


def parse_contacts_file(filename: str, raw: bytes) -> ParsedRows:
    """Transforme un fichier CSV/XLSX en liste de contacts a importer."""
    if len(raw) > MAX_FILE_BYTES:
        raise ImportFileError("Fichier trop gros (max 5 Mo)")
    if not raw:
        raise ImportFileError("Fichier vide")
    is_excel = filename.lower().endswith((".xlsx", ".xlsm"))
    table = _read_xlsx(raw) if is_excel else _read_csv(raw)
    table = [row for row in table if any(str(cell).strip() for cell in row)]
    if len(table) < 2:
        raise ImportFileError("Aucune ligne de contact trouvee")

    mapping = _map_header(table[0])
    rows, errors = [], []
    for line_number, row in enumerate(table[1:], start=2):
        record = {key: str(row[i]).strip() if i < len(row) else "" for i, key in mapping.items()}
        if not record.get("prenom") or not record.get("nom"):
            errors.append(f"Ligne {line_number} : prenom ou nom manquant")
            continue
        rows.append({
            "prenom": record["prenom"],
            "nom": record["nom"],
            "institution": record.get("institution", ""),
            "poste": record.get("poste", ""),
            "civilite": _normalize_civilite(record.get("civilite", "")),
            "email": record.get("email", "").lower(),
        })
    return ParsedRows(rows=rows, errors=errors)
