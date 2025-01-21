import os
import signal
import ssl
import sys

import tornado.ioloop
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult

from baselayer.app.env import load_env
from baselayer.log import make_log


# For SMTP testing
class Authenticator:
    def __call__(self, server, session, envelope, mechanism, auth_data):
        return AuthResult(success=True)


class CustomSMTPHandler:
    async def handle_DATA(self, server, session, envelope):
        peer = session.peer
        mail_from = envelope.mail_from
        rcpt_tos = envelope.rcpt_tos
        data = envelope.content  # type: bytes
        log(f"Receiving message from: {peer}")
        log(f"Message addressed from: {mail_from}")
        log(f"Message addressed to  : {rcpt_tos}")
        log(f"Message length        : {len(data)}")
        return "250 OK"


if __name__ == "__main__":
    env, cfg = load_env()
    log = make_log("testsmtpserver")

    if "test_server" in cfg:
        smtp_port = cfg["test_server.smtp_port"]

        log(f"Listening for test SMTP requests on port {smtp_port}")
        # SMTP TLS context
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        cert_file = os.path.join(os.path.dirname(__file__), "cert.pem")
        key_file = os.path.join(os.path.dirname(__file__), "key.pem")

        context.load_cert_chain(cert_file, key_file)
        handler = CustomSMTPHandler()

        controller = Controller(
            handler,
            hostname="localhost",
            port=smtp_port,
            tls_context=context,
            authenticator=Authenticator(),
        )

        # On process close, close SMTP sub-process
        def signal_handler(sig, frame):
            log("Closing SMTP server")
            controller.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        controller.start()
        tornado.ioloop.IOLoop.current().start()
