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
        sent.append(message)

    with patch.object(mail.smtplib, "SMTP") as smtp:
        smtp.return_value.__enter__.return_value.send_message.side_effect = send
        mail.send_email(recipients, "Subject", "<p>Hi</p>")
    return sent


def test_one_message_per_recipient_with_text_part_and_headers():
    sent = send_to(["a@example.edu", "b@example.edu"])
    assert [message["To"] for message in sent] == ["a@example.edu", "b@example.edu"]
    message = sent[0]
    assert message["From"] == "SkyPortal <no-reply@example.org>"
    assert message["Message-ID"].endswith("@example.org>")
    assert message["Date"]
    assert [part.get_content_type() for part in message.iter_parts()] == [
        "text/plain",
        "text/html",
    ]


def test_one_refused_address_does_not_stop_the_rest():
    sent = send_to(
        ["a@example.edu", "gone@example.edu", "b@example.edu"],
        refuse=["gone@example.edu"],
    )
    assert [message["To"] for message in sent] == ["a@example.edu", "b@example.edu"]
    with pytest.raises(mail.smtplib.SMTPRecipientsRefused):
        send_to(["gone@example.edu"], refuse=["gone@example.edu"])


def test_text_part_keeps_link_addresses():
    assert mail.as_text(f'<p>Open <a href="{LINK}">{LINK}</a></p>') == f"Open {LINK}"
    assert mail.as_text(f'<p><a href="{LINK}">Join</a></p>') == f"Join ({LINK})"
    assert mail.as_text("<p>One</p><ul><li>a</li><li>b</li></ul>") == "One\n\n- a\n- b"


def test_invitation_says_who_sent_it_and_where_it_goes():
    inviter = SimpleNamespace(first_name="Ada", last_name="Lovelace", username="ada")
    text = mail.as_text(
        invitation.invite_body(SimpleNamespace(invited_by=inviter), LINK)
    )
    assert "Ada Lovelace invited you to join SkyPortal" in text
    assert LINK in text
    assert "3 days" in text
