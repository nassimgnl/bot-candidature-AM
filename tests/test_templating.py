from datetime import date

from botnassimgnl.templating import build_context, render

CONTACT = {"civilite": "Madame", "prenom": "Marie", "nom": "Martin", "poste": "VP Sales", "institution": "BNP Paribas"}
PROFILE = {"prenom": "Nassim", "nom": "G", "ecole": "KEDGE", "poste_actuel": "Etudiant"}


def test_render_replaces_all_known_variables():
    context = build_context(CONTACT, PROFILE, today=date(2026, 10, 30))
    text = "{Civilite} {Nom} {Prenom} {Poste} {Institution} {Mon_Prenom} {Mon_Nom} {Mon_Ecole} {Mon_Poste} {Date}"
    assert render(text, context) == "Madame Martin Marie VP Sales BNP Paribas Nassim G KEDGE Etudiant 30/10/2026"


def test_render_accepts_accented_variable_names_from_original_templates():
    context = build_context(CONTACT, PROFILE)
    assert render("{Civilité} {Prénom} {Mon_École} {Mon_Prénom}", context) == "Madame Marie KEDGE Nassim"


def test_render_leaves_unknown_variables_untouched():
    assert render("Bonjour {Inconnu}", build_context(CONTACT, PROFILE)) == "Bonjour {Inconnu}"


def test_render_uses_empty_string_for_missing_values():
    context = build_context({"prenom": "Jean", "nom": "Dupont"}, {})
    assert render("{Poste}|{Mon_Ecole}", context) == "|"
