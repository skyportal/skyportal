from .base import BaseHandler
from baselayer.app.access import auth_or_token

import tornado.web


class LogoutHandler(BaseHandler):
    @auth_or_token
    def get(self):
        self.clear_cookie('user_id')
        self.redirect('/')
