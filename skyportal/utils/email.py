import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from baselayer.app.env import load_env

_, cfg = load_env()


def send_email(recipients, subject, body):
    if cfg.get("email_service") == "sendgrid":
        sendgrid_client = SendGridAPIClient(cfg["twilio.sendgrid_api_key"])
        message = Mail(
            from_email=cfg["twilio.from_email"],
            to_emails=recipients,
            subject=subject,
            html_content=body,
        )
        sendgrid_client.send(message)
    elif cfg.get("email_service") == "smtp":
        smtp_server = smtplib.SMTP(cfg["smtp.host"], cfg["smtp.port"])
        smtp_server.starttls()
        smtp_server.login(cfg["smtp.from_email"], cfg["smtp.password"])
        msg = MIMEMultipart()
        msg["From"] = cfg["smtp.from_email"]
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        try:
            smtp_server.send_message(msg)
        finally:
            smtp_server.quit()
    else:
        raise Exception("Invalid email service; update config.yaml")
