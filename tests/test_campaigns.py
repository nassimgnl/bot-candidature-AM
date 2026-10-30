from dataclasses import replace
from datetime import datetime, timedelta

from insider.campaigns import due_followups, expire_followups, prepare_followups, prepare_initial, utc_now
from insider.mailer import MailerError
from insider.repos import contacts as contacts_repo
from insider.repos.emails import record_email
from insider.repos.profile import update_profile
from insider.sender import SendJob, run_job

STAMP = "%Y-%m-%d %H:%M:%S"


def _contact(conn, **overrides):
    data = {"prenom": "Jean", "nom": "Dupont", "institution": "UBS", "poste": "VP", **overrides}
    return contacts_repo.create_contact(conn, data)


def _mark_sent(conn, contact_id, days_ago, status="envoye", followups=0):
    sent_at = (utc_now() - timedelta(days=days_ago)).strftime(STAMP)
    conn.execute("UPDATE contacts SET status=?, last_sent_at=?, followups_sent=? WHERE id=?",
                 (status, sent_at, followups, contact_id))
    record_email(conn, contact_id, "initial", "Candidature UBS", "corps", "<abc@test>", ok=True)
    conn.commit()


def test_prepare_initial_renders_variables_and_skips_already_contacted(conn):
    update_profile(conn, {"prenom": "Nassim", "nom": "G", "ecole": "KEDGE"})
    fresh = _contact(conn)
    done = _contact(conn, prenom="Paul", nom="Durand")
    no_email = _contact(conn, prenom="Ana", nom="X", institution="Inconnue")
    _mark_sent(conn, done, days_ago=1)
    prep = prepare_initial(conn, contacts_repo.get_contacts(conn, [fresh, done, no_email]),
                           "Candidature {Institution}", "Bonjour {Civilite} {Nom}, {Mon_Ecole}", (), force=False)
    assert [e.contact_id for e in prep.emails] == [fresh]
    assert prep.emails[0].subject == "Candidature UBS"
    assert prep.emails[0].body == "Bonjour Monsieur Dupont, KEDGE"
    assert len(prep.skipped) == 2


def test_prepare_initial_force_resends_in_same_thread(conn):
    contact_id = _contact(conn)
    _mark_sent(conn, contact_id, days_ago=1)
    prep = prepare_initial(conn, contacts_repo.get_contacts(conn, [contact_id]), "s", "b", (), force=True)
    assert prep.emails[0].kind == "relance"
    assert prep.emails[0].in_reply_to == "<abc@test>"


def test_due_followups_respects_delay_max_and_replies(conn, settings):
    due = _contact(conn)
    too_recent = _contact(conn, prenom="B", nom="B")
    maxed = _contact(conn, prenom="C", nom="C")
    replied = _contact(conn, prenom="D", nom="D")
    _mark_sent(conn, due, days_ago=6)
    _mark_sent(conn, too_recent, days_ago=2)
    _mark_sent(conn, maxed, days_ago=6, status="relance", followups=3)
    _mark_sent(conn, replied, days_ago=6, status="repondu")
    assert [c["id"] for c in due_followups(conn, settings)] == [due]


def test_expire_followups_marks_sans_reponse_after_last_followup(conn, settings):
    maxed = _contact(conn)
    _mark_sent(conn, maxed, days_ago=6, status="relance", followups=3)
    assert expire_followups(conn, settings) == 1
    assert contacts_repo.get_contact(conn, maxed)["status"] == "sans_reponse"


def test_prepare_followups_uses_next_step_template_in_thread(conn):
    contact_id = _contact(conn, lang="en")
    _mark_sent(conn, contact_id, days_ago=6, status="relance", followups=1)
    email = prepare_followups(conn, contacts_repo.get_contacts(conn, [contact_id])).emails[0]
    assert email.subject == "Re: Candidature UBS"
    assert email.in_reply_to == "<abc@test>"
    assert "I wanted to briefly follow up" in email.body  # template "Follow-up 2"


def test_run_job_sends_records_and_updates_statuses(conn, settings):
    ok_id = _contact(conn)
    bad_id = _contact(conn, prenom="Paul", nom="Durand")
    items = prepare_initial(conn, contacts_repo.get_contacts(conn, [ok_id, bad_id]), "s", "b", (), False).emails
    sent_to = []

    def fake_send(_settings, email, _sender):
        if email.to.startswith("paul"):
            raise MailerError("refuse")
        sent_to.append(email.to)
        return "<id@test>"

    job = SendJob(id="t", total=len(items))
    run_job(job, settings, items, "Moi", send=fake_send)
    assert (job.status, job.sent, job.failed) == ("done", 1, 1)
    assert sent_to == ["jean.dupont@ubs.com"]
    assert contacts_repo.get_contact(conn, ok_id)["status"] == "envoye"
    assert contacts_repo.get_contact(conn, bad_id)["status"] == "non_contacte"


def test_run_job_followup_increments_counter(conn, settings):
    contact_id = _contact(conn)
    _mark_sent(conn, contact_id, days_ago=6)
    items = prepare_followups(conn, contacts_repo.get_contacts(conn, [contact_id])).emails
    run_job(SendJob(id="f", total=1), settings, items, "Moi", send=lambda *_: "<r@test>")
    contact = contacts_repo.get_contact(conn, contact_id)
    assert (contact["status"], contact["followups_sent"]) == ("relance", 1)


def test_run_job_stops_at_daily_limit(conn, settings):
    ids = [_contact(conn, prenom=f"P{i}", nom="N") for i in range(3)]
    items = prepare_initial(conn, contacts_repo.get_contacts(conn, ids), "s", "b", (), False).emails
    job = SendJob(id="l", total=3)
    run_job(job, replace(settings, daily_send_limit=2), items, "Moi", send=lambda *_: "<x@test>")
    assert (job.status, job.sent) == ("limit", 2)
