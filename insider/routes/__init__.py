"""Enregistrement des pages du site."""

from flask import Flask, flash, redirect, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge


def register_blueprints(app: Flask) -> None:
    from insider.routes import (analytics, compose, contacts, dashboard, formats, pipeline,
                                profile, relances, settings, suivi)

    for module in (dashboard, contacts, suivi, compose, relances, pipeline, analytics,
                   formats, profile, settings):
        app.register_blueprint(module.bp)

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        flash("Fichier trop volumineux (10 Mo maximum).", "error")
        return redirect(request.referrer or url_for("dashboard.index"))
