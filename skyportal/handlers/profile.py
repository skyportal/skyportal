from baselayer.app.handlers.base import BaseHandler

import tornado.web


class ProfileHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        return self.success({'username': self.current_user.username})
