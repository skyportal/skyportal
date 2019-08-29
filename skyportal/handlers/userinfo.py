from .base import BaseHandler
from baselayer.app.access import permissions
from ..models import User

from sqlalchemy.orm import joinedload
import tornado.web


class UserInfoHandler(BaseHandler):
    @permissions(['Manage users'])
    def get(self, user_id=None):
        user = User.query.options(joinedload(User.acls)).get(user_id)
        if user is None:
            return self.success(data={'id': user_id, 'username': 'Not found'})
        else:
            return self.success(data={'user': user})
