from types import SimpleNamespace
from unittest.mock import patch

import pytest

from baselayer.app.env import load_env
from skyportal.models import invitation
from skyportal.utils import email as mail

_, cfg = load_env()

LINK = "https://example.org/login/google-oauth2/?invite_token=abc-123"


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setitem(cfg, "email_service", "smtp")
    monkeypatch.setitem(
        cfg,
        "smtp",
        {
            "from_email": "no-reply@example.org",
            "password": "x",
            "host": "h",
            "port": 587,
        },
    )
    monkeypatch.setitem(cfg["app"], "title", "SkyPortal")
    monkeypatch.setitem(cfg["invitations"], "days_until_expiry", 3)
    monkeypatch.setitem(cfg["invitations"], "email_body_preamble", "")


def send_to(recipients, refuse=()):
    sent = []

    def send(message):
        if message["To"] in refuse:
            raise mail.smtplib.SMTPRecipientsRefused({message["To"]: (550, b"no")})
        sent.append(message["To"])

    with patch.object(mail.smtplib, "SMTP") as server:
        server.return_value.send_message.side_effect = send
        mail.send_email(recipients, "Subject", "<p>Hi</p>")
    return sent


def test_message_carries_a_text_alternative():
    message = mail._build("someone@example.edu", "Subject", "<p>Hello</p>")
    assert message.get_content_type() == "multipart/alternative"
    assert [part.get_content_type() for part in message.walk()][1:] == [
        "text/plain",
        "text/html",
    ]


def test_sender_has_a_name_and_the_message_an_id():
    message = mail._build("someone@example.edu", "Subject", "<p>Hello</p>")
    assert message["From"] == "SkyPortal <no-reply@example.org>"
    assert message["Message-ID"].endswith("@example.org>")


def test_a_batch_is_not_addressed_to_everyone_at_once():
    assert send_to(["a@example.edu", "b@example.edu"]) == [
        "a@example.edu",
        "b@example.edu",
    ]


def test_one_bad_address_does_not_stop_the_rest():
    delivered = send_to(
        ["a@example.edu", "gone@example.edu", "b@example.edu"],
        refuse=["gone@example.edu"],
    )
    assert delivered == ["a@example.edu", "b@example.edu"]


def test_a_refusal_still_raises_when_nobody_was_reached():
    with pytest.raises(mail.smtplib.SMTPRecipientsRefused):
        send_to(["gone@example.edu"], refuse=["gone@example.edu"])


@pytest.mark.parametrize(
    "body,text",
    [
        (f'<p>Open <a href="{LINK}">{LINK}</a></p>', f"Open {LINK}"),
        (f'<p><a href="{LINK}">here</a></p>', f"here: {LINK}"),
        ("<p>One</p><p>Two</p>", "One\n\nTwo"),
    ],
)
def test_the_text_part_keeps_each_link_address(body, text):
    assert mail.as_plain_text(body) == text


def test_the_invitation_says_who_sent_it_and_where_it_goes():
    inviter = SimpleNamespace(first_name="Ada", last_name="Lovelace", username="ada")
    text = mail.as_plain_text(
        invitation.invite_body(SimpleNamespace(invited_by=inviter), LINK)
    )
    assert "Ada Lovelace has invited you" in text
    assert LINK in text
    assert "3 days" in text
    assert "without opening that link" in text


def test_the_invitation_stands_without_an_inviter():
    body = invitation.invite_body(SimpleNamespace(invited_by=None), LINK)
    assert "You have been invited to join" in body
