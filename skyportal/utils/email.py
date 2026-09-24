"""Sending mail that arrives.

Most of what makes a message look like phishing is structural rather than
anything in the text: HTML with no plain-text alternative, a bare address
with no name against it, no Message-ID, and every recipient of a batch
listed in the same To header. Filters weigh all four, and an invitation is
the one message a new user has no reason to trust in the first place.
"""

import html
import re
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from python_http_client.exceptions import BadRequestsError
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from baselayer.app.env import load_env
from baselayer.log import make_log

_, cfg = load_env()
log = make_log("email")

_PARAGRAPH = re.compile(r"(?i)</(?:p|div|h[1-6]|ul|ol|table)\s*>")
_BREAK = re.compile(r"(?i)<(?:br\s*/?|/li|/tr)\s*>")
_LINK = re.compile(r'(?is)<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>')
_TAG = re.compile(r"(?s)<[^>]+>")


def as_plain_text(body):
    """The HTML body as text, keeping each link's address visible.

    A reader who cannot see where a link goes has to take it on faith, and so
    does a filter: the address belongs in the text part, not only behind the
    anchor.
    """
    text = _LINK.sub(_unlink, body)
    text = _PARAGRAPH.sub("\n\n", text)
    text = _BREAK.sub("\n", text)
    text = _TAG.sub("", text)
    text = html.unescape(text)
    # Collapse the runs of blank lines the HTML layout leaves behind.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def _unlink(match):
    """`<a href="X">Y</a>` as text, without saying the address twice when the
    link shows the address it points at."""
    href, label = match.group(1), _TAG.sub("", match.group(2)).strip()
    label = html.unescape(label)
    if not label or label == href:
        return href
    return f"{label}: {href}"


def _sender():
    """The From address, and the name shown against it."""
    address = cfg["smtp.from_email"] if cfg.get("email_service") == "smtp" else None
    address = address or cfg.get("twilio.from_email")
    if not address:
        raise Exception("No sender address configured; set smtp.from_email")
    return cfg.get("app.title") or "SkyPortal", address


def _domain(address):
    return address.rpartition("@")[2] or "localhost"


def _build(recipient, subject, body):
    """One message, to one person, in both text and HTML."""
    name, address = _sender()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((name, address))
    message["To"] = recipient
    # smtplib supplies Date but never this, and a message without one reads as
    # machine-generated bulk to the filters that look.
    message["Message-ID"] = make_msgid(domain=_domain(address))
    message.set_content(as_plain_text(body))
    message.add_alternative(body, subtype="html")
    return message


def _raise_if_nobody_was_reached(refused, recipients):
    """Log the addresses that bounced, and fail only if none were deliverable.

    Callers treat an exception as "this was not sent": an invitation rolls back
    on one, so a refusal has to keep raising when there was a single recipient,
    while a notification to many must survive one bad address among them.
    """
    if not refused:
        return
    log(f"refused by the server: {', '.join(sorted(refused))}")
    if len(refused) == len(recipients):
        raise next(iter(refused.values()))


def send_email(recipients, subject, body):
    """Send one message per recipient, so nobody is shown anyone else's address."""
    service = cfg.get("email_service")
    if service not in ("sendgrid", "smtp"):
        raise Exception("Invalid email service; update config.yaml")

    if isinstance(recipients, str):
        recipients = [recipients]
    recipients = [r for r in recipients if r]
    if not recipients:
        return

    name, address = _sender()
    text = as_plain_text(body)
    refused = {}

    if service == "sendgrid":
        client = SendGridAPIClient(cfg["twilio.sendgrid_api_key"])
        for recipient in recipients:
            try:
                client.send(
                    Mail(
                        from_email=(address, name),
                        to_emails=recipient,
                        subject=subject,
                        plain_text_content=text,
                        html_content=body,
                    )
                )
            except BadRequestsError as e:
                refused[recipient] = e
        _raise_if_nobody_was_reached(refused, recipients)
        return

    server = smtplib.SMTP(cfg["smtp.host"], cfg["smtp.port"])
    try:
        server.starttls()
        server.login(cfg["smtp.from_email"], cfg["smtp.password"])
        for recipient in recipients:
            try:
                server.send_message(_build(recipient, subject, body))
            except smtplib.SMTPRecipientsRefused as e:
                # This address, not the server: the rest of the batch is still
                # deliverable and a notification to fifty people should not be
                # lost to one retired account. Anything else (auth, connection)
                # is not per-recipient and propagates.
                refused[recipient] = e
    finally:
        server.quit()
    _raise_if_nobody_was_reached(refused, recipients)
