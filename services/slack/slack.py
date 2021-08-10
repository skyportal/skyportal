import json

import tornado.ioloop
import tornado.web
import tornado.escape

from baselayer.app.env import load_env
from baselayer.log import make_log

env, cfg = load_env()
log = make_log('slack')


class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json')

    def error(self, code, message):
        self.set_status(code)
        self.write({'message': message})

    def get(self):
        self.write({'hello': 'world'})

    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            return self.error(400, "Invalid JSON")

        self.write({'data_posted': str(data)})


def make_app():
    return tornado.web.Application(
        [
            (r"/", MainHandler),
        ]
    )


if __name__ == "__main__":
    slack_poster = make_app()

    port = cfg['ports.slack']
    slack_poster.listen(port)
    log(f'Listening on port {port}')
    tornado.ioloop.IOLoop.current().start()
