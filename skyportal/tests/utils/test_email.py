"""What a mail server sees, and what its filters weigh.

An invitation is the one message a recipient has no prior reason to trust,
and the things that make it look forged are structural: HTML with no text
alternative, an address with no name against it, no Message-ID, and a batch
addressed to everyone at once.
"""

from unittest.mock import patch

import pytest

import skyportal.models.invitation as invitation_module
import skyportal.utils.email as mail

LINK = "https://example.org/login/google-oauth2/?invite_token=abc-123"


@pytest.fixture(autouse=True)
def configured():
    with (
        patch.dict(mail.cfg, {"email_service": "smtp", "app": {"title": "SkyPortal"}}),
        patch.dict(
            invitation_module.cfg,
            {
                "app": {"title": "SkyPortal"},
                "invitations": {"days_until_expiry": 3, "email_body_preamble": ""},
            },
        ),
    ):
        mail.cfg["smtp"] = {"from_email": "no-reply@example.org"}
        yield


def test_the_message_carries_a_text_alternative():
    # HTML with no text part is the single most common thing a filter counts
    # against a message it has no other reason to distrust.
    message = mail._build("someone@example.edu", "Subject", "<p>Hello</p>")
    assert message.get_content_type() == "multipart/alternative"
    assert [part.get_content_type() for part in message.walk()][1:] == [
        "text/plain",
        "text/html",
    ]


def test_the_sender_has_a_name_and_the_message_an_id():
    message = mail._build("someone@example.edu", "Subject", "<p>Hello</p>")
    assert message["From"] == "SkyPortal <no-reply@example.org>"
    # smtplib supplies Date and never this one.
    assert message["Message-ID"].endswith("@example.org>")


def test_a_batch_is_not_addressed_to_everyone_at_once():
    # One message each: a recipient list in To shows every address to all of
    # them, and reads as bulk mail besides.
    sent = []
    with patch.object(mail.smtplib, "SMTP") as server:
        server.return_value.send_message.side_effect = lambda m: sent.append(m["To"])
        mail.cfg["smtp"] = {
            "from_email": "no-reply@example.org",
            "password": "x",
            "host": "h",
            "port": 587,
        }
        mail.send_email(["a@example.edu", "b@example.edu"], "Subject", "<p>Hi</p>")
    assert sent == ["a@example.edu", "b@example.edu"]


def test_a_link_reads_once_in_the_text_part():
    # The anchor text is the address here, and saying it twice reads as the
    # padding that filters score.
    text = mail.as_plain_text(f'<p>Open <a href="{LINK}">{LINK}</a></p>')
    assert text.count(LINK) == 1


def test_a_link_keeps_its_address_when_the_text_hides_it():
    text = mail.as_plain_text(f'<p><a href="{LINK}">here</a></p>')
    assert text == f"here: {LINK}"


def test_paragraphs_survive_as_blank_lines():
    assert mail.as_plain_text("<p>One</p><p>Two</p>") == "One\n\nTwo"


def test_the_invitation_says_who_sent_it_and_where_it_goes():
    class Inviter:
        first_name, last_name, username = "Ada", "Lovelace", "ada"

    class Target:
        user_email, invited_by = "someone@example.edu", Inviter()

    body = invitation_module.invite_body(Target(), LINK)
    text = mail.as_plain_text(body)
    assert "Ada Lovelace has invited you" in text
    assert LINK in text
    assert "3 days" in text
    # The failure that sent us here: signing in directly cannot work, and the
    # mail is the only place to say so.
    assert "without opening that link" in text


def test_an_inviter_who_cannot_be_read_costs_nothing():
    # This runs inside a flush; a name is not worth failing an invitation over.
    class Exploding:
        @property
        def invited_by(self):
            raise RuntimeError("detached")

        user_email = "someone@example.edu"

    body = invitation_module.invite_body(Exploding(), LINK)
    assert "You have been invited to join" in body


def test_one_bad_address_does_not_stop_the_rest():
    # The batch used to go in a single send_message, where the server refused
    # the bad address and delivered the others; one message each must not make
    # the first refusal cost everyone after it their mail.
    sent = []

    def send(message):
        if message["To"] == "gone@example.edu":
            raise mail.smtplib.SMTPRecipientsRefused({message["To"]: (550, b"no")})
        sent.append(message["To"])

    with patch.object(mail.smtplib, "SMTP") as server:
        server.return_value.send_message.side_effect = send
        mail.cfg["smtp"] = {
            "from_email": "no-reply@example.org",
            "password": "x",
            "host": "h",
            "port": 587,
        }
        mail.send_email(
            ["a@example.edu", "gone@example.edu", "b@example.edu"],
            "Subject",
            "<p>Hi</p>",
        )
    assert sent == ["a@example.edu", "b@example.edu"]


def test_a_refusal_still_raises_when_nobody_was_reached():
    # An invitation has one recipient and rolls back on an exception, so a
    # refusal there has to stay fatal.
    with patch.object(mail.smtplib, "SMTP") as server:
        server.return_value.send_message.side_effect = (
            mail.smtplib.SMTPRecipientsRefused({"gone@example.edu": (550, b"no")})
        )
        mail.cfg["smtp"] = {
            "from_email": "no-reply@example.org",
            "password": "x",
            "host": "h",
            "port": 587,
        }
        with pytest.raises(mail.smtplib.SMTPRecipientsRefused):
            mail.send_email(["gone@example.edu"], "Subject", "<p>Hi</p>")
