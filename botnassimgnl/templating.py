"""Remplacement des variables {Prenom}, {Institution}... dans les templates."""

import re
from datetime import date
from html import escape

VARIABLE_PATTERN = re.compile(r"\{([A-Za-zÀ-ÿ0-9_]+)\}")
URL_PATTERN = re.compile(r"^https?://\S+$", re.IGNORECASE)

# Les deux orthographes (avec et sans accents) sont acceptees.
ALIASES = {
    "Civilite": "civilite", "Civilité": "civilite",
    "Prenom": "prenom", "Prénom": "prenom",
    "Nom": "nom",
    "Poste": "poste",
    "Institution": "institution",
    "Mon_Prenom": "mon_prenom", "Mon_Prénom": "mon_prenom",
    "Mon_Nom": "mon_nom",
    "Mon_Ecole": "mon_ecole", "Mon_École": "mon_ecole",
    "Mon_Poste": "mon_poste",
    "Mon_Telephone": "mon_telephone", "Mon_Téléphone": "mon_telephone",
    "Mon_LinkedIn": "mon_linkedin", "Mon_Linkedin": "mon_linkedin",
    "Date": "date",
}
RESERVED_NAMES = frozenset(name.lower() for name in ALIASES)

VARIABLES_HELP = [
    "{Civilite}", "{Prenom}", "{Nom}", "{Poste}", "{Institution}",
    "{Mon_Prenom}", "{Mon_Nom}", "{Mon_Ecole}", "{Mon_Poste}",
    "{Mon_Telephone}", "{Mon_LinkedIn}", "{Date}",
]

# Texte du lien dans la version HTML ; sinon le nom de la variable.
LINK_LABELS = {"mon_linkedin": "LinkedIn"}
CUSTOM_PREFIX = "perso:"


def build_context(contact: dict, profile: dict, custom_variables: list[dict] | tuple = (),
                  today: date | None = None) -> dict:
    """Assemble les valeurs a injecter pour un contact donne."""
    current = today or date.today()
    custom = {f"{CUSTOM_PREFIX}{v['name'].lower()}": v["value"] or "" for v in custom_variables}
    return {
        "civilite": contact.get("civilite") or "",
        "prenom": contact.get("prenom") or "",
        "nom": contact.get("nom") or "",
        "poste": contact.get("poste") or "",
        "institution": contact.get("institution") or "",
        "mon_prenom": profile.get("prenom") or "",
        "mon_nom": profile.get("nom") or "",
        "mon_ecole": profile.get("ecole") or "",
        "mon_poste": profile.get("poste_actuel") or "",
        "mon_telephone": profile.get("telephone") or "",
        "mon_linkedin": profile.get("linkedin") or "",
        "date": current.strftime("%d/%m/%Y"),
        **custom,
    }


def _context_key(name: str) -> str:
    return ALIASES.get(name) or f"{CUSTOM_PREFIX}{name.lower()}"


def _value(name: str, context: dict) -> str | None:
    """Valeur de la variable, ou None si elle est inconnue (laissee telle quelle)."""
    key = _context_key(name)
    if name not in ALIASES and key not in context:
        return None
    return str(context.get(key, "")).strip()


def render(text: str, context: dict) -> str:
    """Version texte : les variables inconnues restent telles quelles."""

    def replace(match: re.Match) -> str:
        value = _value(match.group(1), context)
        return match.group(0) if value is None else value

    return VARIABLE_PATTERN.sub(replace, text or "")


def _html_value(name: str, context: dict) -> str:
    value = _value(name, context)
    if value is None:
        return escape("{" + name + "}")
    if not URL_PATTERN.match(value):
        return escape(value)
    label = LINK_LABELS.get(_context_key(name)) or name.replace("_", " ")
    return f'<a href="{escape(value)}">{escape(label)}</a>'


def render_html(text: str, context: dict) -> str:
    """Version HTML : texte echappe, retours a la ligne conserves, liens cliquables."""
    source = text or ""
    parts, last = [], 0
    for match in VARIABLE_PATTERN.finditer(source):
        parts.append(escape(source[last:match.start()]))
        parts.append(_html_value(match.group(1), context))
        last = match.end()
    parts.append(escape(source[last:]))
    return "".join(parts).replace("\n", "<br>\n")
