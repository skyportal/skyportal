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
_SPACES = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n\s*\n\s*\n+")


def as_plain_text(body):
    text = _LINK.sub(_unlink, body)
    text = _PARAGRAPH.sub("\n\n", text)
    text = _BREAK.sub("\n", text)
    text = html.unescape(_TAG.sub("", text))
    text = _BLANK_LINES.sub("\n\n", _SPACES.sub(" ", text))
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def _unlink(match):
    href, label = match.group(1), html.unescape(_TAG.sub("", match.group(2)).strip())
    return href if label in ("", href) else f"{label}: {href}"


def _sender():
    address = cfg["smtp.from_email"] if cfg.get("email_service") == "smtp" else None
    address = address or cfg["twilio.from_email"]
    if not address:
        raise Exception("No sender address configured; set smtp.from_email")
    return cfg["app.title"], address


def _build(recipient, subject, body):
    name, address = _sender()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((name, address))
    message["To"] = recipient
    # smtplib adds Date but never Message-ID, and a message without one reads as bulk.
    message["Message-ID"] = make_msgid(domain=address.rpartition("@")[2])
    message.set_content(as_plain_text(body))
    message.add_alternative(body, subtype="html")
    return message


def send_email(recipients, subject, body):
    service = cfg.get("email_service")
    refused = {}

    if service == "sendgrid":
        name, address = _sender()
        text = as_plain_text(body)
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
    elif service == "smtp":
        server = smtplib.SMTP(cfg["smtp.host"], cfg["smtp.port"])
        try:
            server.starttls()
            server.login(cfg["smtp.from_email"], cfg["smtp.password"])
            for recipient in recipients:
                try:
                    server.send_message(_build(recipient, subject, body))
                except smtplib.SMTPRecipientsRefused as e:
                    refused[recipient] = e
        finally:
            server.quit()
    else:
        raise Exception("Invalid email service; update config.yaml")

    if refused:
        log(f"refused by the server: {', '.join(sorted(refused))}")
        if len(refused) == len(recipients):
            raise next(iter(refused.values()))
