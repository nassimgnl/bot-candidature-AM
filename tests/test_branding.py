import pytest

from botnassimgnl import create_app
from botnassimgnl.config import DATABASE_FILENAME, LEGACY_DATABASE_FILENAME, detect_provider
from botnassimgnl.db import connect, init_schema

from tests.test_routes import PAGES


@pytest.mark.parametrize("path", PAGES)
def test_every_page_uses_new_brand_and_has_theme_toggle(client, path):
    html = client.get(path).data.decode()
    assert "BOT nassimgnl" in html
    assert "data-theme-toggle" in html
    assert "insider" not in html.lower()


def test_settings_page_shows_provider_buttons(client):
    html = client.get("/parametres/").data.decode()
    for provider in ("gmail", "outlook", "yahoo", "other"):
        assert f'data-provider="{provider}"' in html
    assert "myaccount.google.com/apppasswords" in html


@pytest.mark.parametrize("host, expected", [
    ("smtp.gmail.com", "gmail"), ("SMTP.OFFICE365.COM", "outlook"),
    ("smtp.mail.yahoo.com", "yahoo"), ("mail.ecole.fr", "other"), ("", "other"),
])
def test_detect_provider(host, expected):
    assert detect_provider(host) == expected


def test_legacy_database_is_renamed_and_contacts_kept(settings):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    legacy = connect(settings.data_dir / LEGACY_DATABASE_FILENAME)
    init_schema(legacy)
    legacy.execute("INSERT INTO contacts (prenom, nom) VALUES ('Jean', 'Dupont')")
    legacy.commit()
    legacy.close()

    create_app(settings)

    assert not (settings.data_dir / LEGACY_DATABASE_FILENAME).exists()
    conn = connect(settings.data_dir / DATABASE_FILENAME)
    assert conn.execute("SELECT prenom FROM contacts").fetchone()[0] == "Jean"
    conn.close()


def test_example_env_values_do_not_count_as_configured(settings):
    from dataclasses import replace

    assert settings.smtp_configured
    assert not replace(settings, smtp_user="ton.adresse@gmail.com").smtp_configured
    assert not replace(settings, smtp_password="xxxx xxxx xxxx xxxx").imap_configured
