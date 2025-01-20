import json
import traceback

import tornado.escape
import tornado.ioloop
import tornado.web
from tornado.httpclient import AsyncHTTPClient

from baselayer.app.env import load_env
from baselayer.log import make_log

env, cfg = load_env()
log = make_log("slack")


class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def error(self, code, message):
        self.set_status(code)
        self.write({"message": message})

    def get(self):
        self.write({"status": "active"})

    async def post(self):
        """
        Handles the error checking and posting to the Slack webhook.
        The Slack Webhook API is described here:
            https://api.slack.com/messaging/webhooks#posting_with_webhooks
        Most important is that we check that we are indeed posting
        to a URL which is consistent with being a Slack URL.
        """
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            err = traceback.format_exc()
            log(err)
            return self.error(400, "Invalid JSON")

        url = data.pop("url", "")
        if not url.startswith(cfg.get("slack.expected_url_preamble", "https://")):
            # refuse to post to a URL which is not the Slack hook
            return self.error(400, "Must supply a proper Slack endpoint to POST")

        http_client = AsyncHTTPClient()
        try:
            response = await http_client.fetch(
                url,
                raise_error=False,
                method="POST",
                body=json.dumps(data),
                headers={"Content-type": "application/json"},
            )
            if response.code != 200:
                log(
                    f"Slack POST failed with code {response.code}: {str(response.body)}"
                )
                return self.error(response.code, str(response.body))
        except Exception as e:
            log(f"Error posting to Slack: {e}")


def make_app():
    return tornado.web.Application(
        [
            (r"/", MainHandler),
        ]
    )


if __name__ == "__main__":
    slack_poster = make_app()

    port = cfg.get("slack.microservice_port", 64100)
    slack_poster.listen(port)
    log(f"Listening on port {port}")
    tornado.ioloop.IOLoop.current().start()
