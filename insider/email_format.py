"""Generation d'adresses email a partir d'un format de banque.

Un format utilise les jetons {prenom}, {nom}, {prenom[0]} et {nom[0]},
par exemple "{prenom}.{nom}@bnpparibas.com" ou "{prenom[0]}{nom}@jefferies.com".
"""

import re
import unicodedata

TOKEN_PATTERN = re.compile(r"\{(prenom|nom)(\[0\])?\}")
ALLOWED_SEPARATORS = re.compile(r"^[a-z0-9._\-]*$")
DOMAIN_PATTERN = re.compile(r"^[a-z0-9\-]+(\.[a-z0-9\-]+)*\.[a-z]{2,}$", re.IGNORECASE)


class EmailFormatError(ValueError):
    """Format d'email invalide."""


def normalize_name_part(value: str) -> str:
    """Retire accents, espaces et apostrophes, passe en minuscules.

    "Hélène De La Tour" -> "helenedelatour", "O'Neil" -> "oneil".
    Les tirets sont conserves ("Jean-Pierre" -> "jean-pierre").
    """
    decomposed = unicodedata.normalize("NFKD", value or "")
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\-]", "", ascii_only.lower())


def validate_format(pattern: str) -> str:
    """Verifie qu'un format est utilisable et le renvoie nettoye."""
    cleaned = (pattern or "").strip()
    local, at, domain = cleaned.partition("@")
    if not at or not DOMAIN_PATTERN.match(domain):
        raise EmailFormatError("Le format doit ressembler a {prenom}.{nom}@banque.com")
    if not TOKEN_PATTERN.search(local):
        raise EmailFormatError("Le format doit contenir au moins {prenom} ou {nom}")
    leftover = TOKEN_PATTERN.sub("", local)
    if not ALLOWED_SEPARATORS.match(leftover.lower()):
        raise EmailFormatError("Seuls {prenom}, {nom}, {prenom[0]}, {nom[0]} et . _ - sont autorises")
    return f"{local}@{domain.lower()}"


def build_email(pattern: str, prenom: str, nom: str) -> str:
    """Construit l'adresse email d'une personne a partir d'un format."""
    first = normalize_name_part(prenom)
    last = normalize_name_part(nom)
    if not first or not last:
        raise EmailFormatError("Prenom et nom sont requis pour generer l'email")
    values = {"prenom": first, "nom": last}

    def replace(match: re.Match) -> str:
        part = values[match.group(1)]
        return part[0] if match.group(2) else part

    local, _, domain = validate_format(pattern).partition("@")
    return f"{TOKEN_PATTERN.sub(replace, local).lower()}@{domain}"


def format_example(pattern: str) -> str:
    """Exemple lisible d'un format, avec John Smith."""
    try:
        return build_email(pattern, "John", "Smith")
    except EmailFormatError:
        return ""
