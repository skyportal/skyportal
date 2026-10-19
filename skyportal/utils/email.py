import html
import re
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

import lxml.html
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from baselayer.app.env import load_env
from baselayer.log import make_log

from .app import get_app_base_url

_, cfg = load_env()
log = make_log("email")

FONT = "font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"

STYLE = (
    "h3{margin:0 0 16px;font-size:18px;line-height:1.4;color:#111827}"
    "h4{margin:20px 0 6px;font-size:14px;color:#374151}"
    "p,ul,pre,blockquote{margin:0 0 14px}"
    "ul{padding-left:20px}"
    "a{color:#1d4ed8}"
    "blockquote{padding:4px 14px;border-left:3px solid #d1d5db;color:#4b5563}"
    "pre{padding:12px;background:#f3f4f6;border-radius:6px;font-size:12px;white-space:pre-wrap}"
)

LAYOUT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{subject}</title>
<style>{style}</style>
</head>
<body style="margin:0;padding:0;background:#f3f4f6">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6">
<tr><td align="center" style="padding:32px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px">
<tr><td style="padding:0 4px 14px;{font};font-size:17px;font-weight:700;color:#111827">{site}</td></tr>
<tr><td style="padding:28px 32px;background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;{font};font-size:15px;line-height:1.6;color:#1f2937">
{body}
</td></tr>
<tr><td style="padding:16px 4px;{font};font-size:12px;line-height:1.5;color:#6b7280">{footer}</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""

BLOCKS = ("p", "div", "h1", "h2", "h3", "h4", "ul", "ol", "pre", "table", "blockquote")


def button(url, label):
    return (
        f'<p style="margin:24px 0"><a href="{html.escape(url)}" style="display:inline-block;'
        "padding:11px 20px;border-radius:6px;background:#1d4ed8;color:#ffffff;"
        f'font-weight:600;text-decoration:none">{html.escape(label)}</a></p>'
    )


def preferences_footer():
    return (
        f"You get this email because email notifications are on for your "
        f"{html.escape(cfg['app.title'])} account. "
        f'<a href="{get_app_base_url()}/profile">Manage notifications</a>'
    )


def as_text(fragment):
    root = lxml.html.fragment_fromstring(fragment, create_parent="div")
    for link in root.iter("a"):
        href, label = link.get("href"), link.text_content().strip()
        if href and href != label:
            link.tail = f" ({href}){link.tail or ''}"
    for item in root.iter("li"):
        item.text = f"- {item.text or ''}"
    for element in root.iter("br", "li", "tr"):
        element.tail = f"\n{element.tail or ''}"
    for element in root.iter(*BLOCKS):
        element.text = f"\n\n{element.text or ''}"
        element.tail = f"\n\n{element.tail or ''}"
    lines = (" ".join(line.split()) for line in root.text_content().splitlines())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def send_email(recipients, subject, body, footer=None):
    service = cfg.get("email_service")
    if service not in ("sendgrid", "smtp"):
        raise Exception("Invalid email service; update config.yaml")

    site = html.escape(cfg["app.title"])
    footer = footer or f'Sent by <a href="{get_app_base_url()}">{site}</a>'
    page = LAYOUT.format(
        subject=html.escape(subject),
        style=STYLE,
        font=FONT,
        site=site,
        body=body,
        footer=footer,
    )
    text = as_text(f"{body}<p>--<br>{footer}</p>")

    if service == "sendgrid":
        SendGridAPIClient(cfg["twilio.sendgrid_api_key"]).send(
            Mail(
                from_email=(cfg["twilio.from_email"], cfg["app.title"]),
                to_emails=list(recipients),
                subject=subject,
                plain_text_content=text,
                html_content=page,
                is_multiple=True,
            )
        )
        return

    address = cfg["smtp.from_email"]
    refused = {}
    with smtplib.SMTP(cfg["smtp.host"], cfg["smtp.port"]) as server:
        if cfg["smtp.password"]:
            server.starttls()
            server.login(address, cfg["smtp.password"])
        for recipient in recipients:
            message = EmailMessage()
            message["From"] = formataddr((cfg["app.title"], address))
            message["To"] = recipient
            message["Subject"] = subject
            message["Date"] = formatdate(localtime=True)
            message["Message-ID"] = make_msgid(domain=address.rpartition("@")[2])
            message.set_content(text)
            message.add_alternative(page, subtype="html")
            try:
                server.send_message(message)
            except smtplib.SMTPRecipientsRefused as e:
                refused.update(e.recipients)

    if refused:
        log(f"Refused recipients: {', '.join(refused)}")
        if len(refused) == len(recipients):
            raise smtplib.SMTPRecipientsRefused(refused)
