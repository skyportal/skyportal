import tornado.web
from baselayer.log import make_log
from ...base import BaseHandler


log = make_log('js')


class LogHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        data = self.get_json()
        log(f"{data['error']}{data['stack']}")
        return self.success()
