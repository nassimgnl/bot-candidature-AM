from flask import Blueprint, render_template

from insider.db import get_db
from insider.repos.emails import sends_per_day
from insider.stats import overview, status_counts

bp = Blueprint("analytics", __name__, url_prefix="/analytics")

CHART_DAYS = 30


@bp.get("/")
def index():
    conn = get_db()
    stats = overview(conn)
    funnel = [
        ("Contacts", stats["contacts"]),
        ("Contactes", stats["contacted"]),
        ("Reponses", stats["replies"]),
        ("Entretiens", stats["interviews"]),
        ("Offres", stats["offers"]),
    ]
    days = sends_per_day(conn, CHART_DAYS)
    return render_template("analytics.html", funnel=funnel, days=days,
                           max_day=max((d["n"] for d in days), default=0),
                           by_status=status_counts(conn), stats=stats)
