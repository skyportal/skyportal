from baselayer.app.handlers.base import BaseHandler
from baselayer.app.access import permissions

import tornado.web


class BecomeUserHandler(BaseHandler):
#    @permissions(['System admin'])
    def get(self, new_user_id=None):
        user_id = self.get_secure_cookie('user_id')
        self.clear_cookie('user_id')
        self.set_secure_cookie('user_id', new_user_id.encode('ascii'))
        self.redirect('/')
