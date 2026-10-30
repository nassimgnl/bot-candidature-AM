import pytest

from insider.email_format import EmailFormatError, build_email, format_example, normalize_name_part, validate_format
from insider.seed_data import INSTITUTIONS, expand_format


@pytest.mark.parametrize("pattern, expected", [
    ("{prenom}.{nom}@bnpparibas.com", "jean.dupont@bnpparibas.com"),
    ("{prenom[0]}{nom}@jefferies.com", "jdupont@jefferies.com"),
    ("{prenom[0]}.{nom}@fnysllc.com", "j.dupont@fnysllc.com"),
    ("{nom}@evercore.com", "dupont@evercore.com"),
    ("{prenom}_{nom}@keybank.com", "jean_dupont@keybank.com"),
    ("{nom}{prenom[0]}@blackstone.com", "dupontj@blackstone.com"),
    ("{prenom}{nom}@optiver.com", "jeandupont@optiver.com"),
])
def test_build_email_supports_every_format_style(pattern, expected):
    assert build_email(pattern, "Jean", "Dupont") == expected


def test_build_email_removes_accents_spaces_and_apostrophes():
    assert build_email("{prenom}.{nom}@sgcib.com", "Hélène", "De La Tour") == "helene.delatour@sgcib.com"
    assert build_email("{prenom}.{nom}@sgcib.com", "Zoë", "O'Neil") == "zoe.oneil@sgcib.com"


def test_build_email_keeps_hyphens_in_compound_names():
    assert normalize_name_part("Jean-Pierre") == "jean-pierre"


def test_build_email_lowercases_domain():
    assert build_email("{prenom}.{nom}@HarrisWilliams.com", "A", "B") == "a.b@harriswilliams.com"


@pytest.mark.parametrize("bad", [
    "", "pas-un-format", "{prenom}.{nom}", "@banque.com", "john@banque.com",
    "{prenom.__class__}@x.com", "{autre}@x.com", "{prenom} {nom}@x.com",
])
def test_validate_format_rejects_invalid_or_dangerous_patterns(bad):
    with pytest.raises(EmailFormatError):
        validate_format(bad)


def test_build_email_requires_both_names():
    with pytest.raises(EmailFormatError):
        build_email("{prenom}.{nom}@x.com", "", "Dupont")


def test_format_example_returns_empty_string_for_invalid_pattern():
    assert format_example("{prenom}.{nom}@x.com") == "john.smith@x.com"
    assert format_example("invalide") == ""


def test_every_seed_format_is_valid():
    for name, entries in INSTITUTIONS:
        for entry in entries:
            assert build_email(expand_format(entry), "John", "Smith"), name
