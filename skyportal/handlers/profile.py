from baselayer.app.handlers.base import BaseHandler
from ..models import User

import tornado.web


class ProfileHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = (User.query.filter(User.username == self.current_user.username)
                    .first())
        user_roles = [role.id for role in user.roles]
        return self.success({'username': self.current_user.username,
                             'roles': user_roles})
