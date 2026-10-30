from botnassimgnl.inbox import InboxMessage, classify
from botnassimgnl.mailer import OutgoingEmail, build_message


def test_build_message_sets_threading_headers_and_attachment(settings, tmp_path):
    cv = tmp_path / "CV.pdf"
    cv.write_bytes(b"%PDF-1.4 test")
    message = build_message(settings, OutgoingEmail(
        to="jean.dupont@ubs.com", subject="Re: Candidature", body="Bonjour",
        attachments=(cv,), in_reply_to="<first@test>"))
    assert message["To"] == "jean.dupont@ubs.com"
    assert message["In-Reply-To"] == "<first@test>"
    assert message["References"] == "<first@test>"
    assert message["Message-ID"].endswith("@test.local>")
    attachments = list(message.iter_attachments())
    assert attachments[0].get_filename() == "CV.pdf"


def test_classify_detects_replies_by_sender_and_thread_and_bounces():
    contacts_by_email = {"jean.dupont@ubs.com": 1, "paul.durand@kkr.com": 2, "ana@x.com": 3}
    messages = [
        InboxMessage(sender="Jean Dupont <Jean.Dupont@ubs.com>", references=()),
        InboxMessage(sender="assistant@kkr.com", references=("<sent-to-paul@test>",)),
        InboxMessage(sender="Mail Delivery Subsystem <mailer-daemon@googlemail.com>", references=(),
                      body="Address not found: ana@x.com"),
        InboxMessage(sender="newsletter@spam.com", references=()),
    ]
    replied, bounced = classify(messages, contacts_by_email, {"<sent-to-paul@test>": 2})
    assert replied == {1, 2}
    assert bounced == {3}
