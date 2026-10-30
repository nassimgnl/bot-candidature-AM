import re
from dataclasses import replace

import pytest

from botnassimgnl import create_app
from botnassimgnl.config import Settings
from botnassimgnl.db import connect


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        smtp_host="smtp.test.local", smtp_port=587, smtp_user="moi@test.local", smtp_password="secret",
        imap_host="imap.test.local", sender_name="Moi Test", send_delay_seconds=0, daily_send_limit=100,
        followup_delay_days=5, followup_max=3, secret_key="test-key", data_dir=tmp_path,
    )


@pytest.fixture
def app(settings):
    application = create_app(settings)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def conn(app, settings):
    connection = connect(settings.database_path)
    yield connection
    connection.close()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf(client) -> str:
    html = client.get("/").data.decode()
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


@pytest.fixture
def unconfigured_settings(settings) -> Settings:
    return replace(settings, smtp_user="", smtp_password="")
