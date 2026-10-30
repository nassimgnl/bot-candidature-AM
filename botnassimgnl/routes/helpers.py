"""Petites fonctions partagees par les routes."""

from flask import current_app, request

from botnassimgnl.config import Settings


def app_settings() -> Settings:
    return current_app.config["SETTINGS"]


def form_ids(field: str = "ids") -> list[int]:
    """Liste d'identifiants envoyee par un formulaire (cases cochees)."""
    values = request.form.getlist(field) or request.form.get(field, "").split(",")
    return [int(value) for value in values if str(value).strip().isdigit()]


def json_ids(payload: dict, field: str = "ids") -> list[int]:
    return [int(value) for value in payload.get(field, []) if str(value).isdigit()]
