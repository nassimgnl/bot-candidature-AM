"""Actions des pages : envoi, relances, templates, profil, parametres (SMTP/IMAP simules)."""

import io
from datetime import timedelta

import pytest

from botnassimgnl import sender
from botnassimgnl.campaigns import utc_now
from botnassimgnl.inbox import InboxReport
from botnassimgnl.mailer import MailerError
from botnassimgnl.repos import contacts as contacts_repo
from botnassimgnl.repos.emails import record_email
from botnassimgnl.repos.templates import list_templates


@pytest.fixture
def captured_jobs(monkeypatch):
    """Remplace l'envoi en arriere-plan : on capture les emails prepares."""
    jobs = []

    def fake_start_job(_settings, items, sender_name, send=None):
        jobs.append({"items": items, "sender": sender_name})
        return sender.SendJob(id="fake", total=len(items), status="done")

    monkeypatch.setattr("botnassimgnl.routes.compose.start_job", fake_start_job)
    monkeypatch.setattr("botnassimgnl.routes.relances.start_job", fake_start_job)
    return jobs


def _contact(conn, **extra):
    return contacts_repo.create_contact(conn, {"prenom": "Jean", "nom": "Dupont", "institution": "UBS", **extra})


def test_compose_send_prepares_rendered_emails_with_cv(client, csrf, conn, captured_jobs):
    client.post("/profil/", data={"csrf_token": csrf, "prenom": "Nassim", "nom": "G",
                                  "cv": (io.BytesIO(b"%PDF"), "CV Nassim.pdf")}, content_type="multipart/form-data")
    contact_id = _contact(conn)
    response = client.post("/compose/send", data={"csrf_token": csrf, "ids": [str(contact_id)], "attach_cv": "1",
                                                  "subject": "Candidature {Institution}", "body": "Bonjour {Nom}"})
    assert response.status_code == 302 and "job=fake" in response.location
    item = captured_jobs[0]["items"][0]
    assert (item.to, item.subject, item.body) == ("jean.dupont@ubs.com", "Candidature UBS", "Bonjour Dupont")
    assert item.attachments[0].name == "CV_Nassim.pdf"
    assert captured_jobs[0]["sender"] == "Moi Test"


def test_compose_send_requires_subject_and_recipients(client, csrf, conn, captured_jobs):
    client.post("/compose/send", data={"csrf_token": csrf, "subject": "", "body": "x"})
    client.post("/compose/send", data={"csrf_token": csrf, "subject": "s", "body": "b"})
    assert captured_jobs == []


def test_compose_send_refuses_without_smtp(unconfigured_settings, captured_jobs):
    from botnassimgnl import create_app

    app = create_app(unconfigured_settings)
    client = app.test_client()
    html = client.get("/compose/").data.decode()
    assert "SMTP non configure" in html


def test_compose_test_email_goes_to_own_address(client, csrf, conn, monkeypatch):
    sent = []
    monkeypatch.setattr("botnassimgnl.routes.compose.send_email", lambda s, email, name: sent.append(email) or "<id>")
    client.post("/compose/test", data={"csrf_token": csrf, "subject": "Hello {Prenom}", "body": "b"})
    assert sent[0].to == "moi@test.local"
    assert sent[0].subject == "[TEST] Hello Jean"


def test_compose_test_email_reports_smtp_error(client, csrf, monkeypatch):
    def boom(*_):
        raise MailerError("refuse")

    monkeypatch.setattr("botnassimgnl.routes.compose.send_email", boom)
    response = client.post("/compose/test", data={"csrf_token": csrf, "subject": "s", "body": "b"},
                           follow_redirects=True)
    assert "Mail test non envoye".encode() in response.data


def test_job_status_and_stop(client, csrf):
    job = sender.SendJob(id="abc", total=2)
    sender._jobs["abc"] = job
    assert client.get("/compose/job/abc").get_json()["total"] == 2
    client.post("/compose/job/abc/stop", json={}, headers={"X-CSRF-Token": csrf})
    assert job.cancel_event.is_set()
    assert client.get("/compose/job/zzz").status_code == 404
    job.status = "done"


def test_template_create_update_delete(client, csrf, conn):
    data = {"csrf_token": csrf, "name": "Mon template", "lang": "fr", "category": "candidature",
            "subject": "S", "body": "B"}
    client.post("/compose/templates", data=data)
    created = next(t for t in list_templates(conn) if t["name"] == "Mon template")
    client.post(f"/compose/templates/{created['id']}", data={**data, "subject": "S2"})
    assert next(t for t in list_templates(conn) if t["id"] == created["id"])["subject"] == "S2"
    client.post(f"/compose/templates/{created['id']}/delete", data={"csrf_token": csrf})
    assert all(t["id"] != created["id"] for t in list_templates(conn))


def test_relances_page_and_send(client, csrf, conn, captured_jobs):
    contact_id = _contact(conn)
    old = (utc_now() - timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE contacts SET status='envoye', last_sent_at=? WHERE id=?", (old, contact_id))
    record_email(conn, contact_id, "initial", "Candidature UBS", "b", "<first@test>", ok=True)
    conn.commit()
    assert b"Relance 1" in client.get("/relances/").data
    client.post("/relances/send", data={"csrf_token": csrf, "ids": [str(contact_id)]})
    item = captured_jobs[0]["items"][0]
    assert item.kind == "relance" and item.in_reply_to == "<first@test>"


def test_relances_send_ignores_contacts_not_due(client, csrf, conn, captured_jobs):
    contact_id = _contact(conn)
    client.post("/relances/send", data={"csrf_token": csrf, "ids": [str(contact_id)]})
    assert captured_jobs == []


def test_settings_smtp_and_imap_tests(client, csrf, monkeypatch):
    monkeypatch.setattr("botnassimgnl.routes.settings.test_connection", lambda _s: None)
    monkeypatch.setattr("botnassimgnl.routes.settings.check_inbox", lambda _c, _s: InboxReport(3, 0, 0))
    assert "Connexion SMTP OK".encode() in client.post("/parametres/test-smtp", data={"csrf_token": csrf},
                                                      follow_redirects=True).data
    assert "3 message(s)".encode() in client.post("/parametres/test-imap", data={"csrf_token": csrf},
                                                 follow_redirects=True).data


def test_dashboard_inbox_check_reports_errors(client, csrf, monkeypatch):
    from botnassimgnl.inbox import InboxError

    def boom(*_):
        raise InboxError("IMAP en panne")

    monkeypatch.setattr("botnassimgnl.routes.dashboard.check_inbox", boom)
    response = client.post("/inbox/check", data={"csrf_token": csrf}, follow_redirects=True)
    assert "IMAP en panne".encode() in response.data


def test_contact_update_and_bulk_status(client, csrf, conn):
    contact_id = _contact(conn)
    client.post(f"/contacts/{contact_id}", data={"csrf_token": csrf, "prenom": "Jean", "nom": "Dupont",
                                                 "poste": "MD", "status": "entretien", "notes": "RDV mardi"})
    contact = contacts_repo.get_contact(conn, contact_id)
    assert (contact["poste"], contact["status"], contact["notes"]) == ("MD", "entretien", "RDV mardi")
    client.post("/contacts/bulk", data={"csrf_token": csrf, "ids": [str(contact_id)], "action": "status:offre"})
    assert contacts_repo.get_contact(conn, contact_id)["status"] == "offre"
    response = client.post("/contacts/bulk", data={"csrf_token": csrf, "ids": [str(contact_id)], "action": "compose"})
    assert f"ids={contact_id}" in response.location


def test_profile_rejects_bad_cv_extension_and_removes_cv(client, csrf):
    response = client.post("/profil/", data={"csrf_token": csrf, "cv": (io.BytesIO(b"x"), "virus.exe")},
                           content_type="multipart/form-data", follow_redirects=True)
    assert "Formats acceptes".encode() in response.data
    assert client.post("/profil/cv/delete", data={"csrf_token": csrf}).status_code == 302


def test_formats_update_and_delete_routes(client, csrf, conn):
    client.post("/formats/", data={"csrf_token": csrf, "name": "Oddo", "patterns": ["{prenom}.{nom}@oddo-bhf.com"]})
    inst_id = conn.execute("SELECT id FROM institutions WHERE name='Oddo'").fetchone()[0]
    client.post(f"/formats/{inst_id}", data={"csrf_token": csrf, "name": "Oddo BHF",
                                             "patterns": ["{prenom[0]}{nom}@oddo-bhf.com"]})
    assert conn.execute("SELECT name FROM institutions WHERE id=?", (inst_id,)).fetchone()[0] == "Oddo BHF"
    bad = client.post(f"/formats/{inst_id}", data={"csrf_token": csrf, "name": "Oddo BHF", "patterns": ["nope"]},
                      follow_redirects=True)
    assert "Le format doit".encode() in bad.data
    client.post(f"/formats/{inst_id}/delete", data={"csrf_token": csrf})
    assert conn.execute("SELECT COUNT(*) FROM institutions WHERE id=?", (inst_id,)).fetchone()[0] == 0
