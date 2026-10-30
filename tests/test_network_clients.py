"""SMTP et IMAP avec des serveurs simules (aucun vrai email n'est envoye)."""

import smtplib
from dataclasses import replace

import pytest

from insider import inbox, mailer
from insider.config import load_settings
from insider.mailer import MailerError, OutgoingEmail
from insider.repos import contacts as contacts_repo
from insider.repos.emails import record_email


class FakeSMTP:
    instances: list["FakeSMTP"] = []
    fail_login = False

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.sent = host, port, []
        FakeSMTP.instances.append(self)

    def ehlo(self):
        pass

    def starttls(self, context=None):
        pass

    def login(self, user, password):
        if FakeSMTP.fail_login:
            raise smtplib.SMTPAuthenticationError(535, b"bad")

    def send_message(self, message):
        self.sent.append(message)

    def quit(self):
        pass


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSMTP.instances, FakeSMTP.fail_login = [], False
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


def test_send_email_uses_starttls_server_and_returns_message_id(settings, fake_smtp):
    message_id = mailer.send_email(settings, OutgoingEmail(to="a@b.com", subject="S", body="B"), "Moi")
    sent = fake_smtp.instances[0].sent[0]
    assert sent["To"] == "a@b.com" and sent["Message-ID"] == message_id
    assert "Moi" in sent["From"]


def test_ssl_port_and_connection_test(settings, fake_smtp):
    mailer.test_connection(replace(settings, smtp_port=465))
    assert fake_smtp.instances[0].port == 465


def test_bad_credentials_give_clear_message(settings, fake_smtp):
    fake_smtp.fail_login = True
    with pytest.raises(MailerError, match="mot de passe d'application"):
        mailer.test_connection(settings)


def test_missing_credentials(unconfigured_settings):
    with pytest.raises(MailerError, match="SMTP non configure"):
        mailer.test_connection(unconfigured_settings)


class FakeIMAP:
    messages: dict[bytes, tuple[bytes, bytes]] = {}

    def __init__(self, host, timeout=None):
        pass

    def login(self, user, password):
        pass

    def select(self, mailbox, readonly=False):
        return "OK", [b"1"]

    def search(self, charset, *criteria):
        return "OK", [b" ".join(FakeIMAP.messages)]

    def fetch(self, msg_id, query):
        headers, body = FakeIMAP.messages[msg_id]
        return "OK", [(b"header", body if "TEXT" in query else headers), b")"]

    def logout(self):
        pass


def test_check_inbox_updates_replies_and_bounces(conn, settings, monkeypatch):
    replied = contacts_repo.create_contact(conn, {"prenom": "Jean", "nom": "Dupont", "institution": "UBS"})
    bounced = contacts_repo.create_contact(conn, {"prenom": "Ana", "nom": "Lopez", "institution": "KKR"})
    for cid in (replied, bounced):
        conn.execute("UPDATE contacts SET status='envoye' WHERE id=?", (cid,))
        record_email(conn, cid, "initial", "S", "B", f"<m{cid}@test>", ok=True)
    conn.commit()
    FakeIMAP.messages = {
        b"1": (b"From: Jean Dupont <jean.dupont@ubs.com>\r\nSubject: Re: S\r\n\r\n", b""),
        b"2": (b"From: Mail Delivery Subsystem <mailer-daemon@googlemail.com>\r\n\r\n",
               b"Your message to ana.lopez@kkr.com could not be delivered"),
    }
    monkeypatch.setattr(inbox.imaplib, "IMAP4_SSL", FakeIMAP)
    report = inbox.check_inbox(conn, settings)
    assert (report.scanned, report.replies, report.bounces) == (2, 1, 1)
    assert contacts_repo.get_contact(conn, replied)["status"] == "repondu"
    assert contacts_repo.get_contact(conn, bounced)["status"] == "bounce"


def test_check_inbox_without_sent_emails_does_nothing(conn, settings):
    assert inbox.check_inbox(conn, settings).scanned == 0


def test_check_inbox_requires_configuration(conn, unconfigured_settings):
    with pytest.raises(inbox.InboxError):
        inbox.check_inbox(conn, unconfigured_settings)


def test_load_settings_reads_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SMTP_USER", "x@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcd")
    monkeypatch.setenv("FOLLOWUP_MAX", "9")
    loaded = load_settings()
    assert loaded.smtp_configured and loaded.followup_max == 3
    monkeypatch.setenv("SEND_DELAY_SECONDS", "vingt")
    with pytest.raises(ValueError, match="SEND_DELAY_SECONDS"):
        load_settings()
