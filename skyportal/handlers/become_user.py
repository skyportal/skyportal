from baselayer.app.handlers.base import BaseHandler

import tornado.web


class BecomeUserHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, new_user_id=None):
        user_id = self.get_secure_cookie('user_id')
        self.clear_cookie('user_id')
        self.set_secure_cookie('user_id', new_user_id.encode('ascii'))
        self.redirect('/')
