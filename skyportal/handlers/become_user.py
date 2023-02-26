import sqlalchemy

from .base import BaseHandler
from ..models import User, DBSession


class BecomeUserHandler(BaseHandler):
    def get(self, new_user_id=None):
        with DBSession() as session:
            try:
                if not (
                    self.cfg['server.auth.debug_login']
                    or {'System admin', 'Become user'}.intersection(
                        set(self.current_user.permissions)
                    )
                ):
                    return self.error("Insufficient permissions")

                user = session.scalars(
                    sqlalchemy.select(User).where(User.id == new_user_id)
                ).first()
                if user is None:
                    return self.error('Invalid user ID.')

                sa = session.query(User).get(user.id).social_auth.first()
                self.clear_cookie('user_id')
                self.clear_cookie('user_oauth_id')
                self.clear_cookie('auth_token')
                self.set_secure_cookie('user_id', new_user_id.encode('ascii'))
                if sa is not None:
                    self.set_secure_cookie('user_oauth_id', sa.uid.encode('ascii'))
                return self.success()
            except Exception as e:
                session.rollback()
                return self.error(f'Could not become user: {e}')
