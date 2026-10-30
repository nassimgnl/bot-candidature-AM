"""Remplacement des variables {Prenom}, {Institution}... dans les templates."""

import re
from datetime import date

VARIABLE_PATTERN = re.compile(r"\{([A-Za-zÀ-ÿ_]+)\}")

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
    "Date": "date",
}

VARIABLES_HELP = [
    "{Civilite}", "{Prenom}", "{Nom}", "{Poste}", "{Institution}",
    "{Mon_Prenom}", "{Mon_Nom}", "{Mon_Ecole}", "{Mon_Poste}", "{Date}",
]


def build_context(contact: dict, profile: dict, today: date | None = None) -> dict:
    """Assemble les valeurs a injecter pour un contact donne."""
    current = today or date.today()
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
        "date": current.strftime("%d/%m/%Y"),
    }


def render(text: str, context: dict) -> str:
    """Remplace les variables connues ; les inconnues restent telles quelles."""

    def replace(match: re.Match) -> str:
        key = ALIASES.get(match.group(1))
        if key is None:
            return match.group(0)
        return str(context.get(key, "")).strip()

    return VARIABLE_PATTERN.sub(replace, text or "")
