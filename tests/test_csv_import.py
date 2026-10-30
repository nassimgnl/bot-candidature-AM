import io

import pytest
from openpyxl import Workbook

from insider.csv_import import MAX_FILE_BYTES, ImportFileError, parse_contacts_file


def test_parses_comma_separated_utf8_with_bom():
    raw = "﻿Prenom,Nom,Institution,Poste,Civilite\nJean,Dupont,Goldman Sachs,Analyst,Monsieur\n".encode("utf-8")
    parsed = parse_contacts_file("c.csv", raw)
    assert parsed.rows == [{"prenom": "Jean", "nom": "Dupont", "institution": "Goldman Sachs",
                            "poste": "Analyst", "civilite": "Monsieur", "email": ""}]


def test_parses_semicolon_and_windows_encoding_with_accented_headers():
    raw = "Prénom;Nom;Banque;Poste;Civilité\nHélène;Martin;BNP Paribas;VP;Mme\n".encode("cp1252")
    row = parse_contacts_file("c.csv", raw).rows[0]
    assert row["prenom"] == "Hélène"
    assert row["institution"] == "BNP Paribas"
    assert row["civilite"] == "Madame"


def test_reports_rows_without_name_and_keeps_others():
    raw = b"Prenom,Nom\nJean,Dupont\n,Sans Prenom\n"
    parsed = parse_contacts_file("c.csv", raw)
    assert len(parsed.rows) == 1
    assert parsed.errors == ["Ligne 3 : prenom ou nom manquant"]


def test_lowercases_explicit_email_column():
    raw = b"Prenom,Nom,Email\nJean,Dupont,Jean.Dupont@GS.com\n"
    assert parse_contacts_file("c.csv", raw).rows[0]["email"] == "jean.dupont@gs.com"


def test_reads_excel_files():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Prenom", "Nom", "Institution"])
    sheet.append(["Marie", "Curie", "Natixis"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    rows = parse_contacts_file("contacts.xlsx", buffer.getvalue()).rows
    assert rows[0]["prenom"] == "Marie" and rows[0]["institution"] == "Natixis"


@pytest.mark.parametrize("raw, message", [
    (b"", "vide"),
    (b"Institution,Poste\nGS,VP\n", "Prenom et Nom"),
    (b"Prenom,Nom\n", "Aucune ligne"),
    (b"x" * (MAX_FILE_BYTES + 1), "trop gros"),
])
def test_rejects_unusable_files(raw, message):
    with pytest.raises(ImportFileError, match=message):
        parse_contacts_file("c.csv", raw)
