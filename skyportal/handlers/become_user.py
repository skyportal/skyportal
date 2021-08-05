from .base import BaseHandler
from ..models import User


class BecomeUserHandler(BaseHandler):
    def get(self, new_user_id=None):
        if (
            self.cfg['server.auth.debug_login']
            or len(
                {'System admin', 'Become user'}.intersection(
                    set(self.current_user.permissions)
                )
            )
            > 0
        ):
            user = User.query.get(new_user_id)
            sa = user.social_auth.first()
            if user:
                self.clear_cookie('user_id')
                self.clear_cookie('user_oauth_id')
                self.clear_cookie('auth_token')
                self.set_secure_cookie('user_id', new_user_id.encode('ascii'))
                if sa is not None:
                    self.set_secure_cookie('user_oauth_id', sa.uid.encode('ascii'))
                return self.success()
            else:
                return self.error('Invalid user ID.')
