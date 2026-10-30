import pytest

from botnassimgnl.repos import contacts as contacts_repo
from botnassimgnl.repos.institutions import (InstitutionError, create_institution, delete_institution,
                                        find_patterns, list_institutions, update_institution)
from botnassimgnl.repos.templates import TemplateError, create_template, followup_template


def test_seed_loads_banks_and_ten_templates(conn):
    names = {i["name"] for i in list_institutions(conn)}
    assert {"BNP Paribas", "Wells Fargo", "Westpac", "Sandler O'Neill", "Societe Generale"} <= names
    assert conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0] == 10


def test_contact_email_generated_from_institution_format(conn):
    contact_id = contacts_repo.create_contact(conn, {"prenom": "Jean", "nom": "Dupont", "institution": "bnp paribas"})
    assert contacts_repo.get_contact(conn, contact_id)["email"] == "jean.dupont@bnpparibas.com"


def test_contact_can_use_alternative_format(conn):
    contact_id = contacts_repo.create_contact(conn, {"prenom": "Jean", "nom": "Dupont", "institution": "Barclays"},
                                              format_index=1)
    assert contacts_repo.get_contact(conn, contact_id)["email"] == "jdupont@barcap.com"


def test_contact_with_unknown_institution_is_created_without_email(conn):
    contact_id = contacts_repo.create_contact(conn, {"prenom": "A", "nom": "B", "institution": "Inconnue SA"})
    assert contacts_repo.get_contact(conn, contact_id)["email"] == ""


def test_duplicate_email_is_rejected(conn):
    data = {"prenom": "Jean", "nom": "Dupont", "institution": "Natixis"}
    contacts_repo.create_contact(conn, data)
    with pytest.raises(contacts_repo.ContactError, match="existe deja"):
        contacts_repo.create_contact(conn, data)


def test_invalid_explicit_email_is_rejected(conn):
    with pytest.raises(contacts_repo.ContactError, match="Email invalide"):
        contacts_repo.create_contact(conn, {"prenom": "A", "nom": "B", "email": "pas-un-email"})


def test_import_rows_reports_created_duplicates_and_missing_emails(conn):
    rows = [
        {"prenom": "Jean", "nom": "Dupont", "institution": "UBS"},
        {"prenom": "Jean", "nom": "Dupont", "institution": "UBS"},
        {"prenom": "Paul", "nom": "Durand", "institution": "Inconnue"},
    ]
    report = contacts_repo.import_rows(conn, rows)
    assert (report.created, report.duplicates, report.without_email) == (2, 1, 1)


def test_filters_and_status_updates(conn):
    first = contacts_repo.create_contact(conn, {"prenom": "Jean", "nom": "Dupont", "institution": "UBS", "poste": "VP"})
    contacts_repo.create_contact(conn, {"prenom": "Paul", "nom": "Durand", "institution": "KKR", "poste": "MD"})
    contacts_repo.set_status(conn, [first], "repondu")
    assert [c["id"] for c in contacts_repo.list_contacts(conn, status="repondu")] == [first]
    assert len(contacts_repo.list_contacts(conn, institution="kkr")) == 1
    assert len(contacts_repo.list_contacts(conn, search="dup")) == 1
    assert contacts_repo.get_contact(conn, first)["replied_at"] is not None
    with pytest.raises(contacts_repo.ContactError):
        contacts_repo.set_status(conn, [first], "nimporte")


def test_institution_crud_and_rename_propagates_to_contacts(conn):
    inst_id = create_institution(conn, "Rothschild", ["{prenom}.{nom}@rothschildandco.com"])
    contacts_repo.create_contact(conn, {"prenom": "A", "nom": "B", "institution": "Rothschild"})
    update_institution(conn, inst_id, "Rothschild & Co", ["{prenom[0]}{nom}@rothschildandco.com", ""])
    assert find_patterns(conn, "rothschild & co") == ["{prenom[0]}{nom}@rothschildandco.com"]
    assert contacts_repo.list_contacts(conn, institution="Rothschild & Co")
    delete_institution(conn, inst_id)
    assert find_patterns(conn, "Rothschild & Co") == []


def test_institution_validation(conn):
    with pytest.raises(InstitutionError):
        create_institution(conn, "BNP Paribas", [])
    with pytest.raises(InstitutionError):
        create_institution(conn, " ", [])


def test_template_validation_and_followup_lookup(conn):
    with pytest.raises(TemplateError):
        create_template(conn, {"name": "x", "lang": "de", "category": "relance", "subject": "s", "body": "b"})
    assert followup_template(conn, "fr", 2)["name"].startswith("Relance 2")
    assert followup_template(conn, "en", 3)["followup_step"] == 3
