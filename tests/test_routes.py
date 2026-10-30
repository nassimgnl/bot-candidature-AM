import io

import pytest

from botnassimgnl.repos import contacts as contacts_repo

PAGES = ["/", "/contacts/", "/contacts/?tab=institution", "/contacts/?tab=poste", "/contacts/?tab=ajouter",
         "/suivi/", "/compose/", "/relances/", "/pipeline/", "/analytics/", "/formats/", "/profil/", "/parametres/"]


@pytest.mark.parametrize("path", PAGES)
def test_every_page_renders(client, path):
    assert client.get(path).status_code == 200


def test_post_without_csrf_token_is_rejected(client):
    assert client.post("/contacts/add", data={"prenom": "A", "nom": "B"}).status_code == 400


def test_add_contact_then_detail_page(client, csrf, conn):
    response = client.post("/contacts/add", data={"csrf_token": csrf, "prenom": "Jean", "nom": "Dupont",
                                                  "institution": "Goldman Sachs"})
    assert response.status_code == 302
    contact = contacts_repo.list_contacts(conn)[0]
    assert contact["email"] == "jean.dupont@gs.com"
    assert b"jean.dupont@gs.com" in client.get(f"/contacts/{contact['id']}").data


def test_csv_import_through_upload(client, csrf, conn):
    csv = "Prenom;Nom;Institution\nMarie;Martin;Natixis\nLuc;Petit;Banque Inconnue\n".encode("utf-8")
    response = client.post("/contacts/import", data={"csrf_token": csrf, "file": (io.BytesIO(csv), "c.csv")},
                           content_type="multipart/form-data", follow_redirects=True)
    assert "2 contact(s) importe(s)".encode() in response.data
    assert {c["email"] for c in contacts_repo.list_contacts(conn)} == {"marie.martin@natixis.com", ""}


def test_formats_page_create_and_preview(client, csrf):
    client.post("/formats/", data={"csrf_token": csrf, "name": "Rothschild",
                                   "patterns": ["{prenom[0]}{nom}@rothschildandco.com"]})
    data = client.get("/contacts/email-preview?prenom=Jean&nom=Dupont&institution=Rothschild").get_json()
    assert data["email"] == "jdupont@rothschildandco.com"
    bad = client.get("/formats/preview?pattern=nimporte").get_json()
    assert bad["ok"] is False


def test_pipeline_move_changes_status(client, csrf, conn):
    contact_id = contacts_repo.create_contact(conn, {"prenom": "A", "nom": "B"})
    ok = client.post("/pipeline/move", json={"id": contact_id, "status": "entretien"}, headers={"X-CSRF-Token": csrf})
    assert ok.get_json() == {"ok": True}
    bad = client.post("/pipeline/move", json={"id": contact_id, "status": "zzz"}, headers={"X-CSRF-Token": csrf})
    assert bad.status_code == 400


def test_compose_preview_renders_for_contact(client, csrf, conn):
    contact_id = contacts_repo.create_contact(conn, {"prenom": "Jean", "nom": "Dupont", "institution": "UBS"})
    data = client.post("/compose/preview", json={"contact_id": contact_id, "subject": "Hello {Institution}",
                                                 "body": "{Civilite} {Nom}"}, headers={"X-CSRF-Token": csrf}).get_json()
    assert data == {"to": "jean.dupont@ubs.com", "subject": "Hello UBS", "body": "Monsieur Dupont"}


def test_bulk_delete(client, csrf, conn):
    ids = [contacts_repo.create_contact(conn, {"prenom": f"P{i}", "nom": "N"}) for i in range(2)]
    client.post("/contacts/bulk", data={"csrf_token": csrf, "ids": [str(i) for i in ids], "action": "delete"})
    assert contacts_repo.list_contacts(conn) == []


def test_profile_save(client, csrf, conn):
    client.post("/profil/", data={"csrf_token": csrf, "prenom": "Nassim", "nom": "G", "ecole": "KEDGE",
                                  "poste_actuel": "M1"})
    assert b'value="KEDGE"' in client.get("/profil/").data
