from .base import BaseHandler
from baselayer.app.models import ACL
from ..models import User


class BecomeUserHandler(BaseHandler):
    def get(self, new_user_id=None):
        if (
            ACL.query.get('Become user') in self.current_user.permissions
            or self.cfg['server.auth.debug_login']
        ):
            if User.query.get(new_user_id):
                self.clear_cookie('user_id')
                self.clear_cookie('auth_token')
                self.set_secure_cookie('user_id', new_user_id.encode('ascii'))
                self.redirect('/')
            else:
                return self.error('Invalid user ID.')
