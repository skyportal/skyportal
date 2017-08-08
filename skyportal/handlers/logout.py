from baselayer.app.handlers.base import BaseHandler

import tornado.web


class LogoutHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.clear_cookie('user_id')
        self.redirect('/')
