"""Statuts d'une candidature, dans l'ordre du pipeline."""

STATUSES = {
    "non_contacte": {"label": "Non contacte", "color": "slate"},
    "envoye": {"label": "Envoye", "color": "sky"},
    "relance": {"label": "Relance", "color": "violet"},
    "repondu": {"label": "Repondu", "color": "emerald"},
    "entretien": {"label": "Entretien", "color": "amber"},
    "offre": {"label": "Offre", "color": "yellow"},
    "sans_reponse": {"label": "Sans reponse", "color": "zinc"},
    "bounce": {"label": "Bounce", "color": "rose"},
    "refuse": {"label": "Refuse", "color": "red"},
}

# Statuts qui signifient "la personne a repondu".
REPLIED = frozenset({"repondu", "entretien", "offre", "refuse"})
# Statuts encore en attente d'une reponse (donc relancables).
AWAITING_REPLY = frozenset({"envoye", "relance"})


def is_valid(status: str) -> bool:
    return status in STATUSES


def label(status: str) -> str:
    return STATUSES.get(status, {}).get("label", status)
