"""Telephone, LinkedIn et variables personnalisees (creees avec le bouton +)."""

import json
from datetime import date

import pytest

from botnassimgnl.db import connect, init_schema
from botnassimgnl.mailer import OutgoingEmail, build_message
from botnassimgnl.repos import variables as variables_repo
from botnassimgnl.repos.profile import get_profile, update_profile
from botnassimgnl.templating import build_context, render, render_html

CONTACT = {"civilite": "Madame", "prenom": "Marie", "nom": "Martin", "poste": "VP", "institution": "UBS"}
PROFILE = {"prenom": "Nassim", "nom": "Goundoul", "telephone": "+33 6 02 73 72 70",
           "linkedin": "https://www.linkedin.com/in/nassim"}
SIGNATURE = "{Mon_Prenom} {Mon_Nom}\n{Mon_Telephone}\n{Mon_LinkedIn}"


def test_plain_text_signature_shows_phone_and_linkedin_url():
    context = build_context(CONTACT, PROFILE)
    assert render(SIGNATURE, context) == "Nassim Goundoul\n+33 6 02 73 72 70\nhttps://www.linkedin.com/in/nassim"


def test_html_signature_turns_linkedin_into_clickable_link():
    html = render_html(SIGNATURE, build_context(CONTACT, PROFILE))
    assert html == ('Nassim Goundoul<br>\n+33 6 02 73 72 70<br>\n'
                    '<a href="https://www.linkedin.com/in/nassim">LinkedIn</a>')


def test_html_escapes_text_and_values():
    contact = {**CONTACT, "institution": "<b>AT&T</b>"}
    html = render_html("Chez {Institution} & co", build_context(contact, PROFILE))
    assert html == "Chez &lt;b&gt;AT&amp;T&lt;/b&gt; &amp; co"


def test_html_never_links_non_http_values():
    profile = {**PROFILE, "linkedin": "javascript:alert(1)"}
    assert "<a" not in render_html("{Mon_LinkedIn}", build_context(CONTACT, profile))


def test_custom_variables_are_rendered_and_url_values_become_links():
    custom = [{"name": "Portfolio", "value": "https://nassim.dev"}, {"name": "Ville", "value": "Paris"}]
    context = build_context(CONTACT, PROFILE, custom, today=date(2026, 10, 30))
    assert render("{Ville} {ville} {Inconnue}", context) == "Paris Paris {Inconnue}"
    assert render_html("{Portfolio}", context) == '<a href="https://nassim.dev">Portfolio</a>'


def test_profile_stores_phone_and_normalizes_linkedin(conn):
    update_profile(conn, {"prenom": "Nassim", "telephone": " +33 6 02 73 72 70 ", "linkedin": "linkedin.com/in/nassim"})
    profile = get_profile(conn)
    assert profile["telephone"] == "+33 6 02 73 72 70"
    assert profile["linkedin"] == "https://linkedin.com/in/nassim"


def test_existing_database_gets_new_profile_columns(tmp_path):
    db = connect(tmp_path / "old.db")
    db.executescript("CREATE TABLE profile (id INTEGER PRIMARY KEY CHECK (id = 1), prenom TEXT NOT NULL DEFAULT '',"
                     " nom TEXT NOT NULL DEFAULT '', ecole TEXT NOT NULL DEFAULT '',"
                     " poste_actuel TEXT NOT NULL DEFAULT '', cv_filename TEXT NOT NULL DEFAULT '');")
    init_schema(db)
    assert get_profile(db)["linkedin"] == ""
    db.close()


def test_variable_crud_and_validation(conn):
    created = variables_repo.create_variable(conn, "{Mon Portfolio}", " https://nassim.dev ")
    assert created == {"id": created["id"], "name": "Mon_Portfolio", "value": "https://nassim.dev"}
    variables_repo.update_variable(conn, created["id"], "https://nassim.fr")
    assert variables_repo.list_variables(conn)[0]["value"] == "https://nassim.fr"
    for bad_name in ("", "1abc", "Prenom", "mon_linkedin", "mon_portfolio", "a-b"):
        with pytest.raises(variables_repo.VariableError):
            variables_repo.create_variable(conn, bad_name, "x")
    variables_repo.delete_variable(conn, created["id"])
    assert variables_repo.list_variables(conn) == []


def test_html_email_has_text_and_html_parts(settings):
    message = build_message(settings, OutgoingEmail(to="a@b.com", subject="S", body="Bonjour",
                                                    html='<a href="https://x.com">LinkedIn</a>'))
    assert message.get_body(("plain",)).get_content().strip() == "Bonjour"
    assert 'href="https://x.com"' in message.get_body(("html",)).get_content()


def _post_json(client, csrf, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json",
                       headers={"X-CSRF-Token": csrf})


def test_variable_routes_create_update_delete(client, csrf):
    created = _post_json(client, csrf, "/compose/variables", {"name": "Ville", "value": "Paris"})
    assert created.status_code == 200
    variable = created.get_json()["variables"][0]
    assert variable["name"] == "Ville"
    assert _post_json(client, csrf, "/compose/variables", {"name": "Ville", "value": "x"}).status_code == 400
    updated = _post_json(client, csrf, f"/compose/variables/{variable['id']}", {"value": "Lyon"})
    assert updated.get_json()["variables"][0]["value"] == "Lyon"
    deleted = _post_json(client, csrf, f"/compose/variables/{variable['id']}/delete", {})
    assert deleted.get_json()["variables"] == []


def test_preview_returns_html_with_profile_link(client, csrf, conn):
    update_profile(conn, {"prenom": "Nassim", "linkedin": "https://www.linkedin.com/in/nassim"})
    data = _post_json(client, csrf, "/compose/preview", {"subject": "S", "body": "{Mon_LinkedIn}"}).get_json()
    assert data["body"] == "https://www.linkedin.com/in/nassim"
    assert data["html"] == '<a href="https://www.linkedin.com/in/nassim">LinkedIn</a>'


def test_compose_page_lists_phone_linkedin_and_plus_button(client):
    html = client.get("/compose/").data.decode()
    assert "{Mon_Telephone}" in html and "{Mon_LinkedIn}" in html
    assert 'id="var-add"' in html
